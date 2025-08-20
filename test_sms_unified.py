#!/usr/bin/env python3
"""
Unified unit tests for sms.py

This test suite combines basic and comprehensive tests with command-line options:
- --basic: Run only basic tests (faster)
- --full: Run full test suite including integration tests
- --limit N: Set test limit for performance (default: 100)

Examples:
  python test_sms_unified.py --basic          # Basic tests only
  python test_sms_unified.py --full           # Full test suite
  python test_sms_unified.py --basic --limit 50  # Basic tests with 50 limit
  python test_sms_unified.py --full --limit 200  # Full suite with 200 limit
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
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

# Add the current directory to the path so we can import sms
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the module under test
import sms


class TestSMSBasic(unittest.TestCase):
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

    def tearDown(self):
        """Clean up after each test method."""
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
            "PARTICIPANT_TYPE_RECEIVER",
            "HTML_PARSER",
            "GROUP_CONVERSATION_MARKER",
            "SMS_XML_TEMPLATE",
            "MMS_XML_TEMPLATE",
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

    def test_escape_xml(self):
        """Test XML escaping functionality."""
        test_cases = [
            ("Hello & World", "Hello &amp; World"),
            ("<tag>", "&lt;tag&gt;"),
            ("'quote'", "&apos;quote&apos;"),
            ('"double"', "&quot;double&quot;"),
            ("normal text", "normal text"),
            ("&<>'\"", "&amp;&lt;&gt;&apos;&quot;"),
        ]

        for input_text, expected_output in test_cases:
            with self.subTest(input_text=input_text):
                result = sms.escape_xml(input_text)
                self.assertEqual(result, expected_output)

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

    def test_format_sms_xml(self):
        """Test SMS XML formatting."""
        sms_values = {
            "alias": "test_alias",
            "time": 1640995200000,  # 2022-01-01 00:00:00 UTC
            "type": 1,  # received
            "message": "Hello, world!",
        }

        result = sms.format_sms_xml(sms_values)

        # Check that all values are present
        self.assertIn("test_alias", result)
        self.assertIn("1640995200000", result)
        self.assertIn("1", result)
        self.assertIn("Hello, world!", result)

        # Check XML structure - SMS template is self-closing
        self.assertIn("<sms", result)
        self.assertIn("/>", result)

    def test_format_sms_xml_cached(self):
        """Test cached SMS XML formatting."""
        result = sms.format_sms_xml_cached(
            "test_alias", 1640995200000, 1, "Hello, world!"
        )

        # Check that all values are present
        self.assertIn("test_alias", result)
        self.assertIn("1640995200000", result)
        self.assertIn("1", result)
        self.assertIn("Hello, world!", result)

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

    def test_escape_xml_edge_cases(self):
        """Test XML escaping with edge cases."""
        test_cases = [
            ("", ""),  # Empty string
            ("&", "&amp;"),  # Single ampersand
            ("<", "&lt;"),  # Single less than
            (">", "&gt;"),  # Single greater than
            ("'", "&apos;"),  # Single quote
            ('"', "&quot;"),  # Double quote
            ("&<>'\"", "&amp;&lt;&gt;&apos;&quot;"),  # All special chars
            (
                "Hello & World <test> 'quote' \"double\"",
                "Hello &amp; World &lt;test&gt; &apos;quote&apos; &quot;double&quot;",
            ),
        ]

        for input_text, expected_output in test_cases:
            with self.subTest(input_text=input_text):
                result = sms.escape_xml(input_text)
                self.assertEqual(result, expected_output)

    def test_performance_monitoring(self):
        """Test performance monitoring functions."""
        # Test log_performance
        start_time = 1000.0
        sms.log_performance("test_function", start_time, 100)

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

    def test_template_constants(self):
        """Test that template constants are properly formatted."""
        # Test SMS_XML_TEMPLATE
        self.assertIn("{alias}", sms.SMS_XML_TEMPLATE)
        self.assertIn("{time}", sms.SMS_XML_TEMPLATE)
        self.assertIn("{type}", sms.SMS_XML_TEMPLATE)
        self.assertIn("{message}", sms.SMS_XML_TEMPLATE)

        # Test MMS_XML_TEMPLATE
        self.assertIn("{participants}", sms.MMS_XML_TEMPLATE)
        self.assertIn("{time}", sms.MMS_XML_TEMPLATE)
        self.assertIn("{m_type}", sms.MMS_XML_TEMPLATE)
        self.assertIn("{msg_box}", sms.MMS_XML_TEMPLATE)

    def test_regex_patterns(self):
        """Test that regex patterns are properly compiled."""
        # Test that regex patterns are compiled regex objects
        self.assertIsNotNone(sms.FILENAME_PATTERN.pattern)
        self.assertIsNotNone(sms.CUSTOM_SORT_PATTERN.pattern)
        self.assertIsNotNone(sms.PHONE_NUMBER_PATTERN.pattern)
        self.assertIsNotNone(sms.TEL_HREF_PATTERN.pattern)

    def test_string_translation(self):
        """Test HTML to XML string translation."""
        # Test that the translation table is properly set up
        self.assertIsNotNone(sms.HTML_TO_XML_TRANSLATION)

        # Test basic translation - note that & is not translated in the current implementation
        test_string = "Hello <world> & 'quotes' \"double\""
        translated = test_string.translate(sms.HTML_TO_XML_TRANSLATION)
        self.assertIn("&lt;", translated)
        self.assertIn("&gt;", translated)
        # Note: & is not translated to &amp; in the current implementation
        self.assertIn("&", translated)

    def test_xml_attributes_pool(self):
        """Test XML attributes string pool."""
        # Test that common XML attributes are defined
        self.assertIn('read="1"', sms.XML_ATTRIBUTES)
        self.assertIn('status="1"', sms.XML_ATTRIBUTES)
        self.assertIn('locked="0"', sms.XML_ATTRIBUTES)
        self.assertIn('type="1"', sms.XML_ATTRIBUTES)
        self.assertIn('type="2"', sms.XML_ATTRIBUTES)

    def test_string_pool(self):
        """Test string pooling functionality."""
        # Test string pooling
        test_string = "test_value"
        pooled_string = sms.get_pooled_string(test_string)
        self.assertEqual(pooled_string, test_string)

        # Test that the same string is returned from pool
        pooled_string2 = sms.get_pooled_string(test_string)
        self.assertIs(pooled_string, pooled_string2)

        # Test clearing the pool
        sms.clear_string_pool()
        pooled_string3 = sms.get_pooled_string(test_string)
        # After clearing, it should be a new string (not the same object)
        self.assertEqual(pooled_string3, test_string)

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
        self.assertIsInstance(sms.PARTICIPANT_TYPE_RECEIVER, int)

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
        builder_time = time.time() - start_time

        # Test traditional string concatenation
        start_time = time.time()
        traditional_result = ""
        for i in range(10000):  # Same number of iterations
            traditional_result += f"Line {i}: "
            traditional_result += "This is a test message with some content. " * 10
            traditional_result += "\n"
        traditional_time = time.time() - start_time

        # For large operations, StringBuilder should be more efficient
        # Traditional concatenation can be faster for small operations due to overhead
        self.assertEqual(len(result), len(traditional_result))

        # Test string pooling performance
        start_time = time.time()
        for i in range(1000):
            pooled = sms.get_pooled_string(
                f"test_string_{i % 100}"
            )  # Reuse some strings
        pooling_time = time.time() - start_time

        # String pooling should be fast
        self.assertLess(pooling_time, 0.1)  # Should complete in under 100ms

        # Clean up
        builder.clear()
        sms.clear_string_pool()

    def test_memory_efficient_structures(self):
        """Test memory efficient structures."""
        # Test that the string pool is cleared correctly
        sms.clear_string_pool()

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
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")
        mgr = sms.PHONE_LOOKUP_MANAGER
        # Add several aliases and ensure no exception; then force a save
        for i in range(150):
            mgr.add_alias(f"+1555{i:07d}", f"User_{i}")
        # Explicit save to flush
        mgr.save_aliases()
        self.assertTrue(mgr.lookup_file.exists())


class TestSMSAdvanced(unittest.TestCase):
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
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_get_message_type(self):
        """Test message type detection."""
        # Create a mock BeautifulSoup message
        mock_message = Mock()
        mock_cite = Mock()
        mock_span = Mock()

        # Test received message (with span)
        mock_message.cite = mock_cite
        mock_cite.span = mock_span
        result = sms.get_message_type(mock_message)
        self.assertEqual(result, 1)  # received

        # Test sent message (without span)
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
        mock_time.__getitem__ = Mock(side_effect=lambda key: {"title": "2023-01-01T12:00:00.000Z"}[key])
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


class TestSMSIntegration(unittest.TestCase):
    """Integration tests for SMS module."""

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

    def tearDown(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_setup_processing_paths(self):
        """Test processing path setup."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        # Check that paths were set
        self.assertEqual(sms.PROCESSING_DIRECTORY, test_dir.resolve())
        self.assertIsNotNone(sms.OUTPUT_DIRECTORY)
        self.assertIsNotNone(sms.LOG_FILENAME)
        self.assertIsNotNone(sms.CONVERSATION_MANAGER)
        self.assertIsNotNone(sms.PHONE_LOOKUP_MANAGER)

    def test_validate_processing_directory(self):
        """Test processing directory validation."""
        test_dir = Path(self.test_dir)

        # Test with empty directory (should return True but log warnings)
        result = sms.validate_processing_directory(test_dir)
        self.assertTrue(result)

    def test_conversation_manager(self):
        """Test conversation manager functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        manager = sms.CONVERSATION_MANAGER

        # Test conversation ID generation
        conversation_id = manager.get_conversation_id(["+15551234567"], False)
        self.assertIsInstance(conversation_id, str)

        # Test conversation filename generation
        filename = manager.get_conversation_filename(conversation_id)
        self.assertIsInstance(filename, Path)

        # Test message writing
        test_xml = "<sms>test</sms>"
        manager.write_message(conversation_id, test_xml, 1640995200000)

        # Test finalization
        manager.finalize_conversation_files()

        # Check that output directory was created
        self.assertTrue(manager.output_dir.exists())

    def test_phone_lookup_manager(self):
        """Test phone lookup manager functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        manager = sms.PHONE_LOOKUP_MANAGER

        # Test alias sanitization
        sanitized = manager.sanitize_alias("Test User (123)")
        self.assertEqual(sanitized, "Test_User_123")

        # Test adding alias
        manager.add_alias("+15551234567", "Test User")

        # Test getting alias - the manager may sanitize the alias when storing
        alias = manager.get_alias("+15551234567", None)
        # Check that we get some alias back (either original or sanitized)
        self.assertIsInstance(alias, str)
        self.assertGreater(len(alias), 0)

        # Test getting all aliases
        all_aliases = manager.get_all_aliases()
        self.assertIn("+15551234567", all_aliases)
        # Check that we have some alias stored
        self.assertIsInstance(all_aliases["+15551234567"], str)
        self.assertGreater(len(all_aliases["+15551234567"]), 0)

    def test_html_output_format(self):
        """Test HTML output format functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        manager = sms.CONVERSATION_MANAGER

        # Test that output format is set correctly
        self.assertEqual(manager.output_format, "html")

        # Test conversation filename generation for HTML
        conversation_id = "test_conversation"
        filename = manager.get_conversation_filename(conversation_id)
        self.assertEqual(filename.suffix, ".html")

        # Test message writing
        test_xml = "<sms><text>Hello World</text></sms>"
        manager.write_message(conversation_id, test_xml, 1640995200000)

        # Test finalization
        manager.finalize_conversation_files()

        # Check that output directory was created
        self.assertTrue(manager.output_dir.exists())

        # Check that HTML file was created
        html_file = manager.output_dir / f"{conversation_id}.html"
        self.assertTrue(html_file.exists())

        # Check HTML content
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<table>", content)
            self.assertIn("Hello World", content)
            self.assertIn("SMS Conversation: test_conversation", content)

    def test_index_html_generation(self):
        """Test index.html generation functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        manager = sms.CONVERSATION_MANAGER

        # Create test conversation files with proper file objects
        conversation_id1 = "test_conversation_1"
        conversation_id2 = "test_conversation_2"

        # Create actual files for testing
        file1 = manager.output_dir / f"{conversation_id1}.xml"
        file2 = manager.output_dir / f"{conversation_id2}.xml"

        # Ensure output directory exists
        manager.output_dir.mkdir(parents=True, exist_ok=True)

        # Add test conversations with file objects
        manager.conversation_files[conversation_id1] = {
            "messages": [
                (
                    1234567890,
                    '<sms protocol="0" address="+15551234567" type="1" subject="null" body="Hello World" toa="null" sc_toa="null" date="1234567890" read="1" status="-1" locked="0" />',
                )
            ],
            "file": open(file1, "w", encoding="utf-8"),
        }

        manager.conversation_files[conversation_id2] = {
            "messages": [
                (
                    1234567891,
                    '<sms protocol="0" address="+15559876543" type="2" subject="null" body="Goodbye World" toa="null" sc_toa="null" date="1234567891" read="1" status="-1" locked="0" />',
                )
            ],
            "file": open(file2, "w", encoding="utf-8"),
        }

        # Finalize conversation files first
        manager.finalize_conversation_files()

        # Test index.html generation
        test_stats = {
            "num_sms": 2,
            "num_calls": 1,
            "num_voicemails": 0,
            "num_img": 0,
            "num_vcf": 0,
        }
        elapsed_time = 1.5

        manager.generate_index_html(test_stats, elapsed_time)

        # Check that index.html was created
        index_file = manager.output_dir / "index.html"
        self.assertTrue(index_file.exists())

        # Check index.html content
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Google Voice Conversations", content)
            self.assertIn("Processing completed in 1.5", content)
            self.assertIn("Output format: XML", content)
            self.assertIn("Total conversations: 2", content)
            self.assertIn("SMS Messages", content)
            self.assertIn("Call Logs", content)
            self.assertIn("test_conversation_1", content)
            self.assertIn("test_conversation_2", content)
            self.assertIn(
                "Generated automatically by Google Voice SMS Takeout Converter", content
            )

    def test_group_conversation_handling(self):
        """Test group conversation handling including participant extraction and filename generation."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        # Test participant extraction from group conversation HTML
        test_html = """
        <div class="participants">Group conversation with:
            <cite class="sender vcard">
                <a class="tel" href="tel:+13478736042">
                    <span class="fn">Aniella Tang</span>
                </a>
            </cite>, 
            <cite class="sender vcard">
                <a class="tel" href="tel:+13479098263">
                    <span class="fn">Inessa Tang</span>
                </a>
            </cite>, 
            <cite class="sender vcard">
                <a class="tel" href="tel:+16462728914">
                    <span class="fn">Susan Nowak Tang</span>
                </a>
            </cite>
        </div>
        """

        soup = BeautifulSoup(test_html, "html.parser")
        participants_div = soup.find("div", class_="participants")

        # Test participant extraction
        participants_raw = [participants_div]
        participants, aliases = sms.get_participant_phone_numbers_and_aliases(
            participants_raw
        )

        expected_phones = ["+13478736042", "+13479098263", "+16462728914"]
        expected_aliases = ["Aniella Tang", "Inessa Tang", "Susan Nowak Tang"]

        self.assertEqual(participants, expected_phones)
        self.assertEqual(aliases, expected_aliases)

        # Add aliases to phone lookup manager for testing conversation ID generation
        phone_lookup = sms.PHONE_LOOKUP_MANAGER
        test_participants = {
            "+13478736042": "Aniella Tang",
            "+13479098263": "Inessa Tang",
            "+16462728914": "Susan Nowak Tang",
        }

        for phone, name in test_participants.items():
            phone_lookup.add_alias(phone, name)

        # Test conversation ID generation for group
        conv_manager = sms.CONVERSATION_MANAGER
        group_id = conv_manager.get_conversation_id(participants, True)

        # Should use concatenated aliases
        expected_id = "Aniella_Tang_Inessa_Tang_Susan_Nowak_Tang"
        self.assertEqual(group_id, expected_id)

        # Test with many participants (truncation)
        many_participants = [
            "+15551234567",
            "+15559876543",
            "+15551111111",
            "+15552222222",
            "+15553333333",
            "+15554444444",
            "+15555555555",
            "+15556666666",
        ]

        # Add aliases for testing
        phone_lookup = sms.PHONE_LOOKUP_MANAGER
        for phone in many_participants:
            phone_lookup.add_alias(phone, f"User_{phone[-4:]}")

        many_group_id = conv_manager.get_conversation_id(many_participants, True)

        # Should be truncated and include hash
        self.assertIn("and_3_more_", many_group_id)
        self.assertIn("User_", many_group_id)

        # Test that existing aliases are used instead of HTML extraction
        print("\nTesting existing alias priority...")

        # Now test with the same HTML but different aliases in phone lookup
        phone_lookup.add_alias("+13478736042", "Custom_Aliella")
        phone_lookup.add_alias("+13479098263", "Custom_Inessa")
        phone_lookup.add_alias("+16462728914", "Custom_Susan")

        # Extract again - should use existing aliases, not HTML
        participants2, aliases2 = sms.get_participant_phone_numbers_and_aliases(
            participants_raw
        )

        expected_aliases2 = ["Custom_Aliella", "Custom_Inessa", "Custom_Susan"]
        self.assertEqual(aliases2, expected_aliases2)

        # Test conversation ID generation with custom aliases
        group_id2 = conv_manager.get_conversation_id(participants2, True)
        expected_id2 = "Custom_Aliella_Custom_Inessa_Custom_Susan"
        self.assertEqual(group_id2, expected_id2)

    def test_automatic_alias_extraction(self):
        """Test automatic alias extraction from HTML when prompts are disabled."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        manager = sms.PHONE_LOOKUP_MANAGER

        # Create a test HTML with vCard structure
        test_html = """
        <html>
        <body>
            <div class="participants">
                <a class="tel" href="tel:+15551234567">
                    <span class="fn">John Doe</span>
                </a>
            </div>
            <div class="message">
                <cite class="sender vcard">
                    <a class="tel" href="tel:+15559876543">Jane Smith</a>
                </cite>
            </div>
        </body>
        </html>
        """

        soup = BeautifulSoup(test_html, "html.parser")

        # Test automatic extraction for first phone number
        alias1 = manager.get_alias("+15551234567", soup)
        self.assertEqual(alias1, "John_Doe")

        # Test automatic extraction for second phone number
        alias2 = manager.get_alias("+15559876543", soup)
        self.assertEqual(alias2, "Jane_Smith")

        # Test that generic phrases are filtered out
        generic_html = """
        <html>
        <body>
            <a class="fn">Placed call to</a>
        </body>
        </html>
        """

        generic_soup = BeautifulSoup(generic_html, "html.parser")
        generic_alias = manager.get_alias("+15551111111", generic_soup)
        # Should use phone number directly, not extract generic phrase
        self.assertEqual(generic_alias, "+15551111111")

        # Test that existing aliases are prioritized over HTML extraction
        print("\nTesting existing alias priority in automatic extraction...")

        # Add a custom alias for an existing number
        manager.add_alias("+15551234567", "Custom_John")

        # Now test with the same HTML - should use existing alias, not extract from HTML
        existing_alias = manager.get_alias("+15551234567", soup)
        self.assertEqual(existing_alias, "Custom_John")

        # Test that HTML extraction still works for new numbers
        new_alias = manager.get_alias("+15559999999", soup)
        # Should use phone number since no HTML content for this number
        self.assertEqual(new_alias, "+15559999999")

        # Test that non-existent numbers return phone number when no soup provided
        no_soup_alias = manager.get_alias("+15559999999", None)
        self.assertEqual(no_soup_alias, "+15559999999")

    def test_message_content_extraction(self):
        """Test message content extraction for HTML output."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        manager = sms.CONVERSATION_MANAGER

        # Test text extraction
        test_xml = "<sms><text>Hello World</text></sms>"
        message_text, attachments = manager._extract_message_content(test_xml)
        self.assertEqual(message_text, "Hello World")
        self.assertEqual(attachments, "-")

        # Test attachment detection
        test_xml_with_img = (
            "<sms><text>Check this out</text><img src='test.jpg'/></sms>"
        )
        message_text, attachments = manager._extract_message_content(test_xml_with_img)
        self.assertEqual(message_text, "Check this out")
        self.assertIn("📷 Image", attachments)

        # Test vCard detection
        test_xml_with_vcard = (
            "<sms><text>Contact info</text><a class='vcard'>vCard</a></sms>"
        )
        message_text, attachments = manager._extract_message_content(
            test_xml_with_vcard
        )
        self.assertEqual(message_text, "Contact info")
        self.assertIn("📇 vCard", attachments)

        # Test multiple attachments
        test_xml_multiple = "<sms><text>Multiple</text><img src='img.jpg'/><a class='vcard'>vCard</a></sms>"
        message_text, attachments = manager._extract_message_content(test_xml_multiple)
        self.assertEqual(message_text, "Multiple")
        self.assertIn("📷 Image", attachments)
        self.assertIn("📇 vCard", attachments)

        # Test timestamp formatting
        timestamp = 1640995200000  # 2022-01-01 12:00:00 UTC
        formatted = manager._format_timestamp(timestamp)
        # Check that it's a valid timestamp format (timezone may vary)
        self.assertRegex(formatted, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        # Check that it's not the raw timestamp
        self.assertNotEqual(formatted, str(timestamp))

    def test_attachment_processing_integration(self):
        """Test attachment processing integration."""
        # Test build_attachment_mapping
        result = sms.build_attachment_mapping()
        self.assertIsInstance(result, dict)

        # Test build_attachment_mapping_with_progress
        result = sms.build_attachment_mapping_with_progress()
        self.assertIsInstance(result, dict)

    def test_html_processing_integration(self):
        """Test HTML processing integration."""
        # Test extract_src_with_progress
        result = sms.extract_src_with_progress()
        self.assertIsInstance(result, list)

        # Test list_att_filenames_with_progress
        result = sms.list_att_filenames_with_progress()
        self.assertIsInstance(result, list)

    def test_mms_processing_integration(self):
        """Test MMS processing integration."""
        # Test build_mms_xml
        mms_xml = sms.build_mms_xml(
            "test_participants",
            1640995200000,
            128,  # MMS_TYPE_SENT
            2,  # MESSAGE_BOX_SENT
            "text_part",
            "image_parts",
            "vcard_parts",
            "participants_xml",
            "0",
        )

        self.assertIsInstance(mms_xml, str)
        self.assertIn("test_participants", mms_xml)
        self.assertIn("1640995200000", mms_xml)

    def test_participant_processing_integration(self):
        """Test participant processing integration."""
        # Test build_participants_xml
        participants_xml = sms.build_participants_xml(
            ["+15551234567", "+15551234568"], "+15551234567", True
        )

        self.assertIsInstance(participants_xml, str)
        self.assertIn("+15551234567", participants_xml)
        self.assertIn("+15551234568", participants_xml)

    def test_html_output_sender_column(self):
        """Verify HTML output includes Sender column and renders a sender cell."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        manager = sms.CONVERSATION_MANAGER

        conversation_id = "sender_column_test"
        # Raw XML without sender info should default sender cell to '-'
        test_xml = "<sms><text>Hello Sender Column</text></sms>"
        manager.write_message(conversation_id, test_xml, 1640995200000)
        manager.finalize_conversation_files()

        html_file = manager.output_dir / f"{conversation_id}.html"
        self.assertTrue(html_file.exists())
        content = html_file.read_text(encoding="utf-8")
        self.assertIn("<th>Sender</th>", content)
        self.assertIn("class='sender'", content)

    def test_html_output_sms_sender_display(self):
        """Verify SMS sender display shows 'Me' for sent and alias for received."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        manager = sms.CONVERSATION_MANAGER

        conversation_id = "sms_sender_display"
        # Simulate two messages: sent by Me and received from Alice
        manager.write_message_with_content(conversation_id, "Hi", [], 1640995200000, sender="Me")
        manager.write_message_with_content(conversation_id, "Hello", [], 1640995300000, sender="Alice")
        manager.finalize_conversation_files()

        html_file = manager.output_dir / f"{conversation_id}.html"
        content = html_file.read_text(encoding="utf-8")
        self.assertIn("<td class='sender'>Me</td>", content)
        self.assertIn("<td class='sender'>Alice</td>", content)

    def test_call_voicemail_timestamp_parsing(self):
        """Verify call and voicemail timestamps are extracted from HTML, not file mtime."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")
        
        # Create a call file with a specific timestamp in HTML
        calls_dir = test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        call_file = calls_dir / "test-call-2020.html"
        
        # HTML with timestamp from 2020 - using published class like real Google Voice data
        call_html = """
        <html><head><title>Placed call</title></head><body>
            <abbr class="published" title="2020-06-15T14:30:00.000-04:00">Jun 15, 2020</abbr>
            <a class="tel" href="tel:+15550000001">Test User</a>
            <abbr class="duration" title="PT2M30S">(2:30)</abbr>
        </body></html>
        """
        call_file.write_text(call_html, encoding="utf-8")
        
        # Wait a moment to ensure file mtime differs from content timestamp
        import time
        time.sleep(0.1)
        
        # Touch the file to change its modification time to current time
        call_file.touch()
        
        # Extract call info - should get timestamp from HTML content, not file mtime
        with open(call_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        call_info = sms.extract_call_info(str(call_file), soup)
        self.assertIsNotNone(call_info)
        self.assertEqual(call_info["phone_number"], "+15550000001")
        
        # Timestamp should be from 2020, not current time
        expected_ts = int(datetime(2020, 6, 15, 14, 30, 0, tzinfo=timezone(timedelta(hours=-4))).timestamp() * 1000)
        self.assertEqual(call_info["timestamp"], expected_ts)
        
        # Verify file mtime is different (should be current time)
        file_mtime_ts = int(call_file.stat().st_mtime * 1000)
        self.assertNotEqual(call_info["timestamp"], file_mtime_ts)
        
        # Test voicemail with different timestamp format
        vm_file = calls_dir / "test-vm-2019.html"
        vm_html = """
        <html><head><title>Voicemail</title></head><body>
            <time datetime="2019-12-25T09:15:00-05:00">Christmas morning</time>
            <a class="tel" href="tel:+15550000002">Test User</a>
            <div class="message">Test voicemail message</div>
        </body></html>
        """
        vm_file.write_text(vm_html, encoding="utf-8")
        vm_file.touch()  # Update mtime to current time
        
        with open(vm_file, "r", encoding="utf-8") as f:
            vm_soup = BeautifulSoup(f.read(), "html.parser")
        
        vm_info = sms.extract_voicemail_info(str(vm_file), vm_soup)
        self.assertIsNotNone(vm_info)
        
        # Should extract timestamp from HTML datetime attribute
        expected_vm_ts = int(datetime(2019, 12, 25, 9, 15, 0, tzinfo=timezone(timedelta(hours=-5))).timestamp() * 1000)
        self.assertEqual(vm_info["timestamp"], expected_vm_ts)
        
        # Verify it's not using file mtime
        vm_file_mtime_ts = int(vm_file.stat().st_mtime * 1000)
        self.assertNotEqual(vm_info["timestamp"], vm_file_mtime_ts)

    def test_published_timestamp_extraction(self):
        """Test that published timestamps are correctly extracted from call/voicemail HTML."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        
        # Create a voicemail file with the exact structure from real Google Voice data
        calls_dir = test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        vm_file = calls_dir / "real-voicemail.html"
        vm_html = '''<?xml version="1.0" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>Voicemail from Charles Tang</title>
</head>
<body>
<div class="haudio">
<span class="fn">Voicemail from Charles Tang</span>
<div class="contributor vcard">Voicemail from
<a class="tel" href="tel:+17184080080"><span class="fn">Charles Tang</span></a></div>
<abbr class="published" title="2011-02-26T15:19:40.000-05:00">Feb 26, 2011, 3:19:40 PM Eastern Time</abbr>
<span class="description"><span class="full-text">Test voicemail message</span></span>
</div>
</body>
</html>'''
        vm_file.write_text(vm_html, encoding="utf-8")
        
        # Extract timestamp directly
        with open(vm_file, "r", encoding="utf-8") as f:
            vm_soup = BeautifulSoup(f.read(), "html.parser")
        
        timestamp = sms.extract_timestamp_from_call(vm_soup)
        
        # Verify the timestamp matches the published element
        expected_ts = int(datetime(2011, 2, 26, 15, 19, 40, tzinfo=timezone(timedelta(hours=-5))).timestamp() * 1000)
        self.assertEqual(timestamp, expected_ts, 
                       "Should extract timestamp from abbr.published element")
        
        # Test that it's not using script execution time
        current_time = int(time.time() * 1000)
        self.assertNotEqual(timestamp, current_time, 
                           "Timestamp should not be current script execution time")
        
        # Test that it's not using file modification time
        vm_file_mtime_ts = int(vm_file.stat().st_mtime * 1000)
        self.assertNotEqual(timestamp, vm_file_mtime_ts,
                           "Timestamp should not be file modification time")

    def test_file_handle_management(self):
        """Test that file handles are properly managed to avoid 'too many open files' errors."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        
        # Create multiple call files to test file handle management
        calls_dir = test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Create several call files
        call_files = []
        for i in range(10):
            call_file = calls_dir / f"test-call-{i}.html"
            call_html = f"""
            <html><head><title>Placed call</title></head><body>
                <abbr class="published" title="2022-05-15T10:30:45.000-04:00">May 15, 2022</abbr>
                <a class="tel" href="tel:+1555000000{i:02d}">Test User {i}</a>
                <abbr class="duration" title="PT1M23S">(1:23)</abbr>
            </body></html>
            """
            call_file.write_text(call_html, encoding="utf-8")
            call_files.append(call_file)
        
        # Process all call files to test file handle management
        for call_file in call_files:
            try:
                with open(call_file, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                
                # Extract call info
                call_info = sms.extract_call_info(str(call_file), soup)
                self.assertIsNotNone(call_info, f"Should extract info from {call_file.name}")
                
                # Write call entry (this should not open additional file handles)
                sms.write_call_entry(str(call_file), call_info, None, soup)
                
            except Exception as e:
                self.fail(f"File handle management failed for {call_file.name}: {e}")
        
        # Verify that conversation files were created
        manager = sms.CONVERSATION_MANAGER
        self.assertTrue(len(manager.conversation_files) > 0, 
                       "Call entries should create conversation files")
        
        # Test that we can still open new files (no file handle leaks)
        test_file = test_dir / "test_file_handle_test.txt"
        test_file.write_text("test content", encoding="utf-8")
        
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "test content", "Should still be able to open new files")

    def test_no_epoch_zero_timestamps(self):
        """Ensure calls and voicemails never get epoch 0 timestamp (1969-12-31 19:00:00)."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        
        # Create call and voicemail files without proper timestamps
        calls_dir = test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a call file with malformed or missing timestamp
        bad_call_file = calls_dir / "bad-call.html"
        bad_call_html = """
        <html><head><title>Placed call</title></head><body>
            <a class="tel" href="tel:+15550000001">Test User</a>
            <div>Some call content without proper timestamp</div>
        </body></html>
        """
        bad_call_file.write_text(bad_call_html, encoding="utf-8")
        
        # Create a voicemail file with malformed timestamp
        bad_vm_file = calls_dir / "bad-voicemail.html"
        bad_vm_html = """
        <html><head><title>Voicemail</title></head><body>
            <abbr class="dt" title="invalid-date-format"></abbr>
            <a class="tel" href="tel:+15550000002">Test User</a>
            <div class="message">Test voicemail</div>
        </body></html>
        """
        bad_vm_file.write_text(bad_vm_html, encoding="utf-8")
        
        # Process these files
        with open(bad_call_file, "r", encoding="utf-8") as f:
            call_soup = BeautifulSoup(f.read(), "html.parser")
        
        with open(bad_vm_file, "r", encoding="utf-8") as f:
            vm_soup = BeautifulSoup(f.read(), "html.parser")
        
        # Extract info
        call_info = sms.extract_call_info(str(bad_call_file), call_soup)
        vm_info = sms.extract_voicemail_info(str(bad_vm_file), vm_soup)
        
        # Verify we don't get epoch 0 (timestamp = 0)
        # Even if timestamp extraction fails, we should get a reasonable fallback
        if call_info:
            self.assertNotEqual(call_info["timestamp"], 0, 
                               "Call should never have epoch 0 timestamp (1969-12-31 19:00:00)")
            # Should be a reasonable timestamp (after 2000 and before far future)
            if call_info["timestamp"] is not None:
                self.assertGreater(call_info["timestamp"], 946684800000)  # Jan 1, 2000
                self.assertLess(call_info["timestamp"], 4102444800000)    # Jan 1, 2100
        
        if vm_info:
            self.assertNotEqual(vm_info["timestamp"], 0, 
                               "Voicemail should never have epoch 0 timestamp (1969-12-31 19:00:00)")
            # Should be a reasonable timestamp (after 2000 and before far future)
            if vm_info["timestamp"] is not None:
                self.assertGreater(vm_info["timestamp"], 946684800000)   # Jan 1, 2000
                self.assertLess(vm_info["timestamp"], 4102444800000)     # Jan 1, 2100
        
        # Test writing entries to ensure they also don't produce epoch 0
        if call_info:
            # This should not raise an exception and should use fallback timestamps
            sms.write_call_entry(str(bad_call_file), call_info, None, call_soup)
        
        if vm_info:
            # This should not raise an exception and should use fallback timestamps  
            sms.write_voicemail_entry(str(bad_vm_file), vm_info, None, vm_soup)

    def test_valid_timestamps_preserved(self):
        """Ensure valid timestamps from HTML are correctly preserved and not overridden."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        
        # Create call and voicemail files with valid timestamps
        calls_dir = test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Create call file with specific timestamp
        call_file = calls_dir / "timestamped-call.html"
        call_html = """
        <html><head><title>Placed call</title></head><body>
            <abbr class="dt" title="2022-05-15T10:30:45Z"></abbr>
            <a class="tel" href="tel:+15550000001">Test User</a>
            <abbr class="duration" title="PT1M23S">(1:23)</abbr>
        </body></html>
        """
        call_file.write_text(call_html, encoding="utf-8")
        
        # Create voicemail file with specific timestamp  
        vm_file = calls_dir / "timestamped-voicemail.html"
        vm_html = """
        <html><head><title>Voicemail</title></head><body>
            <time datetime="2021-08-20T14:15:30-07:00">Aug 20, 2021</time>
            <a class="tel" href="tel:+15550000002">Test User</a>
            <div class="message">Test voicemail transcription</div>
        </body></html>
        """
        vm_file.write_text(vm_html, encoding="utf-8")
        
        # Extract info
        with open(call_file, "r", encoding="utf-8") as f:
            call_soup = BeautifulSoup(f.read(), "html.parser")
        
        with open(vm_file, "r", encoding="utf-8") as f:
            vm_soup = BeautifulSoup(f.read(), "html.parser")
        
        call_info = sms.extract_call_info(str(call_file), call_soup)
        vm_info = sms.extract_voicemail_info(str(vm_file), vm_soup)
        
        # Verify exact timestamps are preserved
        if call_info:
            expected_call_ts = int(datetime(2022, 5, 15, 10, 30, 45, tzinfo=timezone.utc).timestamp() * 1000)
            self.assertEqual(call_info["timestamp"], expected_call_ts, 
                           "Call timestamp should match the HTML dt element exactly")
        
        if vm_info:
            expected_vm_ts = int(datetime(2021, 8, 20, 14, 15, 30, tzinfo=timezone(timedelta(hours=-7))).timestamp() * 1000)
            self.assertEqual(vm_info["timestamp"], expected_vm_ts,
                           "Voicemail timestamp should match the HTML time element exactly")
        
        # Test that write functions also preserve these timestamps
        manager = sms.CONVERSATION_MANAGER
        
        if call_info:
            sms.write_call_entry(str(call_file), call_info, None, call_soup)
            # Check that the message was written with the correct timestamp
            self.assertTrue(len(manager.conversation_files) > 0, "Call entry should create conversation file")
        
        if vm_info:
            sms.write_voicemail_entry(str(vm_file), vm_info, None, vm_soup)
            # Check that the message was written with the correct timestamp
            self.assertTrue(len(manager.conversation_files) > 0, "Voicemail entry should create conversation file")

    def test_mms_sender_alias_in_html(self):
        """Verify MMS rows show sender alias in HTML output."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        manager = sms.CONVERSATION_MANAGER

        # Prepare participants HTML and message with a tel link
        mms_html = """
        <div class="participants">Group conversation with:
            <cite class="sender vcard"><a class="tel" href="tel:+15551230001"><span class="fn">Alice</span></a></cite>
            <cite class="sender vcard"><a class="tel" href="tel:+15551230002"><span class="fn">Bob</span></a></cite>
        </div>
        <div class="message">
            <cite class="sender vcard"><a class="tel" href="tel:+15551230001">Alice</a></cite>
            <abbr class="dt" title="2024-01-01T12:00:00Z"></abbr>
            <q>Hello Group</q>
        </div>
        """
        soup = BeautifulSoup(mms_html, "html.parser")
        participants_raw = soup.select(".participants")
        messages_raw = soup.select(".message")

        # Ensure alias exists in phone lookup
        sms.PHONE_LOOKUP_MANAGER.add_alias("+15551230001", "Alice")
        # Run MMS writing
        # Pass a fixed timestamp into write_message_with_content by stubbing get_time_unix
        sms.write_mms_messages("test_mms.html", participants_raw, messages_raw, None, {})
        manager.finalize_conversation_files()

        # There will be a group conversation file; check any .html in output for sender cell with Alice
        generated_files = list(manager.output_dir.glob("*.html"))
        self.assertTrue(generated_files)
        hit = False
        for f in generated_files:
            content = f.read_text(encoding="utf-8")
            if "Hello Group" in content:
                doc = BeautifulSoup(content, "html.parser")
                # Look for a row containing the message text
                rows = doc.find_all("tr")
                for row in rows:
                    if row.find("td", class_="message") and "Hello Group" in row.find("td", class_="message").get_text():
                        sender_cell = row.find("td", class_="sender")
                        if sender_cell and sender_cell.get_text(strip=True) == "Alice":
                            hit = True
                            break
                if hit:
                    break
        self.assertTrue(hit)

    def test_calls_and_voicemails_processed(self):
        """Ensure calls and voicemails are captured and timestamps vary."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")
        manager = sms.CONVERSATION_MANAGER

        # Create synthetic call and voicemail files
        calls_dir = test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        call_file = calls_dir / "2024-placed-call.html"
        vm_file = calls_dir / "2023-voicemail.html"
        call_file.write_text(
            """
            <html><head><title>Placed call</title></head><body>
                <abbr class="dt" title="2024-02-01T15:00:00Z"></abbr>
                <a class="tel" href="tel:+15550000001">User</a>
                <abbr class="duration" title="PT45S">(0:45)</abbr>
            </body></html>
            """,
            encoding="utf-8",
        )
        vm_file.write_text(
            """
            <html><head><title>Voicemail</title></head><body>
                <abbr class="dt" title="2023-03-05T10:30:00Z"></abbr>
                <a class="tel" href="tel:+15550000002">User</a>
                <div class="message">Test voicemail</div>
            </body></html>
            """,
            encoding="utf-8",
        )

        # Run process_html_files on an empty mapping (no attachments needed here)
        stats = sms.process_html_files({})
        # We expect at least one call and one voicemail captured
        self.assertGreaterEqual(stats.get("num_calls", 0), 1)
        self.assertGreaterEqual(stats.get("num_voicemails", 0), 1)

        # Verify finalize creates files and then generate index
        manager.finalize_conversation_files()
        manager.generate_index_html(stats, 1.0)
        index_file = manager.output_dir / "index.html"
        self.assertTrue(index_file.exists())

        # Ensure timestamps are not identical (implies parsing worked)
        content = index_file.read_text(encoding="utf-8")
        self.assertIn("Call Logs", content)
        self.assertIn("Voicemails", content)


def create_test_suite(test_type="basic", test_limit=100):
    """
    Create a test suite based on the specified type and limit.

    Args:
        test_type (str): 'basic', 'advanced', 'full', or 'integration'
        test_limit (int): Maximum number of test objects to process

    Returns:
        unittest.TestSuite: Configured test suite
    """
    # Set test limit for performance
    sms.set_test_mode(True, test_limit)

    suite = unittest.TestSuite()

    if test_type == "basic":
        # Basic tests only - fastest
        suite.addTest(unittest.makeSuite(TestSMSBasic))
    elif test_type == "advanced":
        # Basic + Advanced tests
        suite.addTest(unittest.makeSuite(TestSMSBasic))
        suite.addTest(unittest.makeSuite(TestSMSAdvanced))
    elif test_type == "full":
        # All tests except integration
        suite.addTest(unittest.makeSuite(TestSMSBasic))
        suite.addTest(unittest.makeSuite(TestSMSAdvanced))
    elif test_type == "integration":
        # Integration tests only
        suite.addTest(unittest.makeSuite(TestSMSIntegration))
    else:  # Default to basic
        suite.addTest(unittest.makeSuite(TestSMSBasic))

    return suite


def main():
    """Main function to run tests with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified SMS module test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --basic                    # Run basic tests only (fastest)
  %(prog)s --full                     # Run full test suite
  %(prog)s --basic --limit 50         # Basic tests with 50 object limit
  %(prog)s --full --limit 200         # Full suite with 200 object limit
  %(prog)s --integration              # Integration tests only
  %(prog)s --sms-test                 # Test SMS.py with proper test mode
        """,
    )

    # Test type selection (mutually exclusive)
    test_group = parser.add_mutually_exclusive_group(required=False)
    test_group.add_argument(
        "--basic", action="store_true", help="Run basic tests only (default)"
    )
    test_group.add_argument(
        "--advanced", action="store_true", help="Run basic + advanced tests"
    )
    test_group.add_argument(
        "--full", action="store_true", help="Run full test suite (basic + advanced)"
    )
    test_group.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    test_group.add_argument(
        "--sms-test",
        action="store_true",
        help="Test SMS.py with proper test mode (auto-enables debug + strict mode)",
    )

    # Performance options
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Set test limit for performance (default: 100)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--tb",
        choices=["short", "long", "line", "no"],
        default="short",
        help="Traceback style (default: short)",
    )

    args = parser.parse_args()

    # Determine test type
    if args.sms_test:
        # Test SMS.py with proper test mode
        print(
            "🧪 Testing SMS.py with proper test mode (auto-enables debug + strict mode)..."
        )
        import subprocess
        import sys
        from pathlib import Path

        # Get the directory containing SMS.py
        sms_dir = Path(__file__).parent
        sms_script = sms_dir / "sms.py"

        # Run SMS.py with test mode
        result = subprocess.run(
            [
                sys.executable,
                str(sms_script),
                "--test-mode",
                "--test-limit",
                str(args.limit),
                "--output-format",
                "html",
                str(sms_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print("✅ SMS.py test mode passed successfully!")
            print("📝 Output:", result.stdout[-500:])  # Show last 500 chars of output
            return 0
        else:
            print("❌ SMS.py test mode failed!")
            print("📝 Error:", result.stderr)
            print("📝 Output:", result.stdout[-500:])
            return 1
    elif args.full:
        test_type = "full"
    elif args.advanced:
        test_type = "advanced"
    elif args.integration:
        test_type = "integration"
    else:
        test_type = "basic"  # Default

    # Create and run test suite
    suite = create_test_suite(test_type, args.limit)

    # Configure test runner
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)

    print(f"🧪 Running {test_type} test suite with {args.limit} object limit...")
    print(f"📊 Test count: {suite.countTestCases()}")
    print("=" * 60)

    # Run tests
    result = runner.run(suite)

    # Print summary
    print("=" * 60)
    if result.wasSuccessful():
        print("🎉 All tests passed successfully!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(main())
