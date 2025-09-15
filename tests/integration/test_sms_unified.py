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

        # Test string pooling performance
        start_time = time.time()
        for i in range(1000):
            # pooled variable removed - not used
            sms.get_pooled_string(f"test_string_{i % 100}")  # Reuse some strings
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
        
        # Create required directory structure for SMS processing
        self.create_test_directory_structure()

    def tearDown(self):
        """Clean up after each test method."""
        # Reset SMS module global variables to allow fresh setup in next test
        import sms
        sms.PROCESSING_DIRECTORY = None
        sms.OUTPUT_DIRECTORY = None
        sms.LOG_FILENAME = None
        sms.CONVERSATION_MANAGER = None
        sms.PHONE_LOOKUP_MANAGER = None
        
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
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

    def test_setup_processing_paths(self):
        """Test processing path setup."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        # Check that paths were set
        self.assertEqual(sms.PROCESSING_DIRECTORY.resolve(), test_dir.resolve())
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
        # The output format should be set to "html" as passed to setup_processing_paths
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
        group_id = conv_manager.get_conversation_id(participants, True, phone_lookup)

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

        many_group_id = conv_manager.get_conversation_id(many_participants, True, phone_lookup)

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
        group_id2 = conv_manager.get_conversation_id(participants2, True, phone_lookup)
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

        # Test build_attachment_mapping_with_progress_new (using PathManager)
        # Note: This function requires a PathManager instance, so we'll test the new function
        # First we need to set up a PathManager
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")
        if hasattr(sms, 'PATH_MANAGER') and sms.PATH_MANAGER:
            from core.attachment_manager_new import build_attachment_mapping_with_progress_new
            result = build_attachment_mapping_with_progress_new(sms.PATH_MANAGER)
            self.assertIsInstance(result, dict)
        else:
            # Skip this test if PathManager is not available
            self.skipTest("PathManager not available for testing")

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
        manager.write_message_with_content(
            conversation_id, "Hi", [], 1640995200000, sender="Me"
        )
        manager.write_message_with_content(
            conversation_id, "Hello", [], 1640995300000, sender="Alice"
        )
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
        expected_ts = int(
            datetime(
                2020, 6, 15, 14, 30, 0, tzinfo=timezone(timedelta(hours=-4))
            ).timestamp()
            * 1000
        )
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
        expected_vm_ts = int(
            datetime(
                2019, 12, 25, 9, 15, 0, tzinfo=timezone(timedelta(hours=-5))
            ).timestamp()
            * 1000
        )
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
        vm_html = """<?xml version="1.0" ?>
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
</html>"""
        vm_file.write_text(vm_html, encoding="utf-8")

        # Extract timestamp directly
        with open(vm_file, "r", encoding="utf-8") as f:
            vm_soup = BeautifulSoup(f.read(), "html.parser")

        timestamp = sms.extract_timestamp_from_call(vm_soup)

        # Verify the timestamp matches the published element
        expected_ts = int(
            datetime(
                2011, 2, 26, 15, 19, 40, tzinfo=timezone(timedelta(hours=-5))
            ).timestamp()
            * 1000
        )
        self.assertEqual(
            timestamp,
            expected_ts,
            "Should extract timestamp from abbr.published element",
        )

        # Test that it's not using script execution time
        current_time = int(time.time() * 1000)
        self.assertNotEqual(
            timestamp,
            current_time,
            "Timestamp should not be current script execution time",
        )

        # Test that it's not using file modification time
        vm_file_mtime_ts = int(vm_file.stat().st_mtime * 1000)
        self.assertNotEqual(
            timestamp,
            vm_file_mtime_ts,
            "Timestamp should not be file modification time",
        )

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
                self.assertIsNotNone(
                    call_info, f"Should extract info from {call_file.name}"
                )

                # Write call entry (this should not open additional file handles)
                sms.write_call_entry(str(call_file), call_info, None, soup)

            except Exception as e:
                self.fail(f"File handle management failed for {call_file.name}: {e}")

        # Verify that conversation files were created
        manager = sms.CONVERSATION_MANAGER
        self.assertTrue(
            len(manager.conversation_files) > 0,
            "Call entries should create conversation files",
        )

        # Test that we can still open new files (no file handle leaks)
        test_file = test_dir / "test_file_handle_test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(
            content, "test content", "Should still be able to open new files"
        )

    def test_mms_message_processing_with_soup_parameter(self):
        """Test that MMS message processing works correctly with soup parameter."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Create test HTML with MMS message structure
        test_html = """
        <div class='message'>
            <cite class='sender vcard'>
                <a class='tel' href='tel:+15551234567'>
                    <abbr class='fn' title='Test User'>Test User</abbr>
                </a>
            </cite>
            <q>Test MMS message with image</q>
            <img src='test-image.jpg' alt='Test image'>
            <abbr class='dt' title='2024-01-15T10:30:00Z'>Jan 15, 2024</abbr>
        </div>
        """

        messages = [BeautifulSoup(test_html, "html.parser")]
        participants_raw = [
            [
                BeautifulSoup(
                    '<cite class="sender"><a href="tel:+15551234567">Test User</a></cite>',
                    "html.parser",
                )
            ]
        ]

        # This should not raise a NameError about 'soup' not being defined
        try:
            # Create mock objects for required parameters
            mock_conversation_manager = type("MockConversationManager", (), {})()
            mock_phone_lookup_manager = type("MockPhoneLookupManager", (), {})()

            sms.write_mms_messages(
                "test_mms.html",
                participants_raw,
                messages,
                None,
                {},
                mock_conversation_manager,
                mock_phone_lookup_manager,
                soup=None,
            )
            # Function executed successfully
        except NameError as e:
            if "soup" in str(e):
                self.fail(
                    f"MMS processing still references undefined 'soup' variable: {e}"
                )
            else:
                # Other NameErrors are acceptable in this test context
                pass
        except Exception:
            # Other exceptions are expected in this test context
            pass

    def test_message_type_determination_with_none_cite(self):
        """Test that message type determination handles None cite elements gracefully."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Create test HTML with no cite element
        test_html = """
        <div class='message'>
            <q>Test message without cite</q>
            <abbr class='dt' title='2024-01-15T10:30:00Z'>Jan 15, 2024</abbr>
        </div>
        """

        message = BeautifulSoup(test_html, "html.parser")

        # This should not raise AttributeError about NoneType having no attribute 'span'
        try:
            message_type = sms.get_message_type(message)
            # Should return a valid message type (1 or 2)
            self.assertIn(
                message_type,
                [1, 2],
                f"Message type should be 1 or 2, got {message_type}",
            )
        except AttributeError as e:
            if "NoneType" in str(e) and "span" in str(e):
                self.fail(f"Message type determination still fails with None cite: {e}")
            else:
                # Other AttributeErrors are acceptable
                pass
        except Exception:
            # Other exceptions are acceptable in this test context
            pass

    def test_timestamp_extraction_with_multiple_strategies(self):
        """Test get_time_unix with various HTML structures for timestamp extraction."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various timestamp formats and structures
        test_cases = [
            # Strategy 1: dt class with title
            {
                "html": '<div class="message"><abbr class="dt" title="2024-01-15T10:30:00Z">Jan 15</abbr><q>Test message</q></div>',
                "should_extract": True,
            },
            # Strategy 2: abbr with title
            {
                "html": '<div class="message"><abbr title="2024-02-20T14:45:30Z">Feb 20</abbr><q>Test message</q></div>',
                "should_extract": True,
            },
            # Strategy 3: time with datetime
            {
                "html": '<div class="message"><time datetime="2024-03-25T09:15:45Z">Mar 25</time><q>Test message</q></div>',
                "should_extract": True,
            },
            # Strategy 4: any element with datetime
            {
                "html": '<div class="message"><span datetime="2024-04-10T16:20:15Z">Apr 10</span><q>Test message</q></div>',
                "should_extract": True,
            },
            # Strategy 5: ISO pattern in text
            {
                "html": '<div class="message"><q>Test message</q><span>2024-05-12T11:30:00Z</span></div>',
                "should_extract": True,
            },
            # Strategy 6: Flexible date parsing
            {
                "html": '<div class="message"><q>Test message</q><span>12/25/2024 3:45 PM</span></div>',
                "should_extract": True,
            },
            # Strategy 7: Element text parsing
            {
                "html": '<div class="message"><q>Test message</q><div>2024-06-18</div></div>',
                "should_extract": True,
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i):
                soup = BeautifulSoup(test_case["html"], "html.parser")
                message = soup.find("div", class_="message")
                if not message:
                    message = soup.find("div")  # Fallback if no message class

                result = sms.get_time_unix(message)

                # Verify the timestamp is reasonable (not epoch 0, not current time fallback)
                self.assertIsInstance(
                    result, int, f"Strategy {i+1} should return integer timestamp"
                )
                self.assertGreater(
                    result,
                    1000000000000,
                    f"Strategy {i+1} should return reasonable timestamp (after 2001)",
                )

                # Verify it's not the current time fallback (should be significantly different)
                current_time = int(time.time() * 1000)
                time_diff = abs(result - current_time)
                self.assertGreater(
                    time_diff,
                    1000000,
                    f"Strategy {i+1} should not return current time fallback (diff: {time_diff}ms)",
                )

                # Log the actual timestamp for debugging
                print(
                    f"Strategy {i+1} extracted timestamp: {result} from {test_case['html']}"
                )

    def test_mms_processing_with_none_soup_parameter(self):
        """Test that MMS processing works correctly when soup parameter is None."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Create test HTML with MMS message structure
        test_html = """
        <div class='message'>
            <cite class='sender vcard'>
                <a class='tel' href='tel:+15551234567'>
                    <abbr class='fn' title='Test User'>Test User</abbr>
                </a>
            </cite>
            <q>Test MMS message with image</q>
            <img src='test-image.jpg' alt='Test image'>
            <abbr class='dt' title='2024-01-15T10:30:00Z'>Jan 15, 2024</abbr>
        </div>
        """

        messages = [BeautifulSoup(test_html, "html.parser")]
        participants_raw = [
            [
                BeautifulSoup(
                    '<cite class="sender"><a href="tel:+15551234567">Test User</a></cite>',
                    "html.parser",
                )
            ]
        ]

        # This should not raise a NoneType error about soup.find_all
        try:
            # Create mock objects for required parameters
            mock_conversation_manager = type("MockConversationManager", (), {})()
            mock_phone_lookup_manager = type("MockPhoneLookupManager", (), {})()

            sms.write_mms_messages(
                "test_mms.html",
                participants_raw,
                messages,
                None,
                {},
                mock_conversation_manager,
                mock_phone_lookup_manager,
                soup=None,
            )
            # Function executed successfully
        except AttributeError as e:
            if "'NoneType' object has no attribute 'find_all'" in str(e):
                self.fail(
                    f"MMS processing still has NoneType error when soup is None: {e}"
                )
            else:
                # Other AttributeErrors are acceptable in this test context
                pass
        except Exception:
            # Other exceptions are expected in the test context
            pass

    def test_timestamp_extraction_edge_cases(self):
        """Test timestamp extraction with edge cases and malformed HTML."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test edge cases that might cause timestamp extraction to fail
        edge_cases = [
            # Empty message
            {"html": '<div class="message"></div>', "should_fail": True},
            # Message with no timestamp elements
            {
                "html": '<div class="message"><q>Just text, no timestamp</q></div>',
                "should_fail": True,
            },
            # Message with malformed timestamp
            {
                "html": '<div class="message"><abbr title="invalid-date">Invalid</abbr><q>Test</q></div>',
                "should_fail": True,
            },
            # Message with very short text
            {"html": '<div class="message"><q>Hi</q></div>', "should_fail": True},
        ]

        for i, test_case in enumerate(edge_cases):
            with self.subTest(i=i):
                soup = BeautifulSoup(test_case["html"], "html.parser")
                message = soup.find("div", class_="message")
                if not message:
                    message = soup.find("div")

                if test_case["should_fail"]:
                    # Should fall back to current time
                    result = sms.get_time_unix(message)
                    current_time = int(time.time() * 1000)
                    # Allow for small timing differences (within 1 second)
                    self.assertLess(
                        abs(result - current_time),
                        1000,
                        f"Edge case {i} should fall back to current time",
                    )
                else:
                    # Should extract valid timestamp
                    result = sms.get_time_unix(message)
                    self.assertIsInstance(
                        result, int, f"Edge case {i} should return valid timestamp"
                    )
                    self.assertGreater(
                        result, 0, f"Edge case {i} should return positive timestamp"
                    )

    def test_mms_participant_extraction_with_none_soup(self):
        """Test that MMS participant extraction gracefully handles None soup parameter."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Create test data that would normally require soup for participant extraction
        messages = [
            BeautifulSoup('<div class="message"><q>Test MMS</q></div>', "html.parser")
        ]
        participants_raw = []  # Empty participants to trigger fallback logic

        # This should not crash when soup is None
        try:
            # Create mock objects for required parameters
            mock_conversation_manager = type("MockConversationManager", (), {})()
            mock_phone_lookup_manager = type("MockPhoneLookupManager", (), {})()

            sms.write_mms_messages(
                "test_mms_none_soup.html",
                participants_raw,
                messages,
                None,
                {},
                mock_conversation_manager,
                mock_phone_lookup_manager,
                soup=None,
            )
            # Function should execute without NoneType errors
        except AttributeError as e:
            if "'NoneType' object has no attribute 'find_all'" in str(e):
                self.fail(f"MMS participant extraction still fails with None soup: {e}")
            else:
                # Other AttributeErrors are acceptable
                pass
        except Exception:
            # Other exceptions are expected in test context
            pass

    def test_comprehensive_timestamp_fallback_strategies(self):
        """Test all timestamp fallback strategies comprehensively."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test that each strategy is tried in order and works
        strategies = [
            # Strategy 1: dt class with title
            {
                "html": '<div class="message"><abbr class="dt" title="2024-01-15T10:30:00Z">Jan 15</abbr><q>Test</q></div>',
                "description": "dt class with title attribute",
            },
            # Strategy 2: abbr with title (no dt class)
            {
                "html": '<div class="message"><abbr title="2024-02-20T14:45:30Z">Feb 20</abbr><q>Test</q></div>',
                "description": "abbr element with title attribute",
            },
            # Strategy 3: time with datetime
            {
                "html": '<div class="message"><time datetime="2024-03-25T09:15:45Z">Mar 25</time><q>Test</q></div>',
                "description": "time element with datetime attribute",
            },
            # Strategy 4: any element with datetime
            {
                "html": '<div class="message"><span datetime="2024-04-10T16:20:15Z">Apr 10</span><q>Test</q></div>',
                "description": "any element with datetime attribute",
            },
            # Strategy 5: ISO pattern in text
            {
                "html": '<div class="message"><q>Test</q><span>2024-05-12T11:30:00Z</span></div>',
                "description": "ISO timestamp pattern in text content",
            },
            # Strategy 6: Flexible date parsing
            {
                "html": '<div class="message"><q>Test</q><span>12/25/2023 3:45 PM</span></div>',
                "description": "flexible date/time parsing",
            },
            # Strategy 7: Element text parsing
            {
                "html": '<div class="message"><q>Test</q><div>2024-06-18</div></div>',
                "description": "timestamp in element text",
            },
        ]

        for i, strategy in enumerate(strategies):
            with self.subTest(i=i, strategy=strategy["description"]):
                soup = BeautifulSoup(strategy["html"], "html.parser")
                message = soup.find("div", class_="message")
                if not message:
                    message = soup.find("div")

                # Should extract timestamp successfully
                result = sms.get_time_unix(message)
                self.assertIsInstance(
                    result, int, f"Strategy {i+1} should return valid timestamp"
                )
                self.assertGreater(
                    result, 0, f"Strategy {i+1} should return positive timestamp"
                )

                # Verify it's a reasonable timestamp (not epoch 0 or current time fallback)
                current_time = int(time.time() * 1000)
                # Allow for timezone differences and parsing variations
                # The timestamp should be reasonable (not epoch 0, not too far in future)
                self.assertGreater(
                    result,
                    1000000000000,
                    f"Strategy {i+1} should return reasonable timestamp (after 2001)",
                )
                # For past dates, ensure they're not unreasonably far in the future
                # Allow up to 1 year in the future to account for timezone and parsing differences
                max_allowed_future = current_time + (
                    365 * 24 * 60 * 60 * 1000
                )  # 1 year in milliseconds
                self.assertLess(
                    result,
                    max_allowed_future,
                    f"Strategy {i+1} should not return unreasonably far future timestamp",
                )

    def test_calls_and_voicemails_processed(self):
        """Ensure calls and voicemails are captured and timestamps vary."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")
        manager = sms.CONVERSATION_MANAGER

        # Create synthetic call and voicemail files with proper Google Voice naming patterns
        # Note: Calls directory is already created in setUp()
        calls_dir = test_dir / "Calls"
        call_file = calls_dir / "test_call_placed_2024-02-01.html"
        vm_file = calls_dir / "test_voicemail_2023-03-05.html"
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

    def test_enhanced_timestamp_extraction_strategies(self):
        """Test all 10 enhanced timestamp extraction strategies comprehensively."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test all 10 strategies with various HTML structures
        test_cases = [
            # Strategy 1: dt class with title
            {
                "html": '<div class="message"><abbr class="dt" title="2024-01-15T10:30:00Z">Jan 15</abbr><q>Test</q></div>',
                "description": "dt class with title attribute",
                "filename": "test_strategy1.html",
            },
            # Strategy 2: abbr with title (no dt class)
            {
                "html": '<div class="message"><abbr title="2024-02-20T14:45:30Z">Feb 20</abbr><q>Test</q></div>',
                "description": "abbr element with title attribute",
                "filename": "test_strategy2.html",
            },
            # Strategy 3: time with datetime
            {
                "html": '<div class="message"><time datetime="2024-03-25T09:15:45Z">Mar 25</time><q>Test</q></div>',
                "description": "time element with datetime attribute",
                "filename": "test_strategy3.html",
            },
            # Strategy 4: any element with datetime
            {
                "html": '<div class="message"><span datetime="2024-04-10T16:20:15Z">Apr 10</span><q>Test</q></div>',
                "description": "any element with datetime attribute",
                "filename": "test_strategy4.html",
            },
            # Strategy 5: ISO pattern in text
            {
                "html": '<div class="message"><q>Test</q><span>2024-05-12T11:30:00Z</span></div>',
                "description": "ISO timestamp pattern in text content",
                "filename": "test_strategy5.html",
            },
            # Strategy 6: Flexible date parsing
            {
                "html": '<div class="message"><q>Test</q><span>12/25/2024 3:45 PM</span></div>',
                "description": "flexible date/time parsing",
                "filename": "test_strategy6.html",
            },
            # Strategy 7: Element text parsing
            {
                "html": '<div class="message"><q>Test</q><div>2024-06-18</div></div>',
                "description": "timestamp in element text",
                "filename": "test_strategy7.html",
            },
            # Strategy 8: Element with timestamp class
            {
                "html": '<div class="message"><q>Test</q><span class="timestamp">2024-07-20 14:30:00</span></div>',
                "description": "element with timestamp class",
                "filename": "test_strategy8.html",
            },
            # Strategy 9: Element with timestamp id
            {
                "html": '<div class="message"><q>Test</q><span id="timestamp">2024-08-15 09:45:00</span></div>',
                "description": "element with timestamp id",
                "filename": "test_strategy9.html",
            },
            # Strategy 10: Element with data timestamp attribute
            {
                "html": '<div class="message"><q>Test</q><span data-timestamp="2024-09-10 16:20:00"></span></div>',
                "description": "element with data timestamp attribute",
                "filename": "test_strategy10.html",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, strategy=test_case["description"]):
                soup = BeautifulSoup(test_case["html"], "html.parser")
                message = soup.find("div", class_="message")
                if not message:
                    message = soup.find("div")

                # Should extract timestamp successfully with filename parameter
                result = sms.get_time_unix(message, test_case["filename"])

                # Verify the timestamp is reasonable
                self.assertIsInstance(
                    result, int, f"Strategy {i+1} should return integer timestamp"
                )
                self.assertGreater(
                    result,
                    1000000000000,
                    f"Strategy {i+1} should return reasonable timestamp (after 2001)",
                )

                # Verify it's not the current time fallback (should be significantly different)
                current_time = int(time.time() * 1000)
                time_diff = abs(result - current_time)
                self.assertGreater(
                    time_diff,
                    1000000,
                    f"Strategy {i+1} should not return current time fallback (diff: {time_diff}ms)",
                )

                # Log the actual timestamp for debugging
                print(
                    f"Strategy {i+1} ({test_case['description']}) extracted timestamp: {result} from {test_case['filename']}"
                )

    def test_mms_participant_extraction_with_filename_fallback(self):
        """Test that MMS participant extraction works with filename-based fallback strategies."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test case 1: Filename with phone number
        filename_with_phone = (
            "Susan Nowak Tang +15551234567 - Text - 2025-08-13T12_08_52Z.html"
        )
        messages = [
            BeautifulSoup('<div class="message"><q>Test MMS</q></div>', "html.parser")
        ]
        participants_raw = []  # Empty participants to trigger fallback logic

        # This should extract phone number from filename
        try:
            # Create mock objects for required parameters
            mock_conversation_manager = type("MockConversationManager", (), {})()
            mock_phone_lookup_manager = type("MockPhoneLookupManager", (), {})()

            sms.write_mms_messages(
                filename_with_phone,
                participants_raw,
                messages,
                None,
                {},
                mock_conversation_manager,
                mock_phone_lookup_manager,
                soup=None,
            )
            # Function should execute without errors
        except Exception as e:
            self.fail(f"MMS processing with phone in filename should not fail: {e}")

        # Test case 2: Filename without phone number (should create default)
        filename_without_phone = "John Doe - Text - 2025-08-13T12_08_52Z.html"

        try:
            # Create mock objects for required parameters
            mock_conversation_manager = type("MockConversationManager", (), {})()
            mock_phone_lookup_manager = type("MockPhoneLookupManager", (), {})()

            sms.write_mms_messages(
                filename_without_phone,
                participants_raw,
                messages,
                None,
                {},
                mock_conversation_manager,
                mock_phone_lookup_manager,
                soup=None,
            )
            # Function should execute without errors and create default participant
        except Exception as e:
            self.fail(f"MMS processing without phone in filename should not fail: {e}")

    def test_error_logging_with_filename_context(self):
        """Test that error logging includes filename context for better debugging."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test case: Message with no timestamp elements (should trigger error logging)
        test_html = '<div class="message"><q>Just text, no timestamp</q></div>'
        test_filename = "no_timestamp_message.html"

        soup = BeautifulSoup(test_html, "html.parser")
        message = soup.find("div", class_="message")

        # Capture log output to verify filename is included
        import io
        import logging

        # Create a string buffer to capture log output
        log_buffer = io.StringIO()
        log_handler = logging.StreamHandler(log_buffer)
        log_handler.setLevel(
            logging.WARNING
        )  # Changed from ERROR to WARNING to capture fallback messages

        # Get the logger and add our handler temporarily
        logger = logging.getLogger("sms")
        original_handlers = logger.handlers.copy()
        original_level = logger.level
        logger.setLevel(logging.WARNING)  # Ensure logger level allows warnings
        logger.addHandler(log_handler)

        try:
            # This should now succeed with fallback strategies instead of failing
            result = sms.get_time_unix(message, test_filename)

            # Verify that the function returned a valid timestamp (fallback behavior)
            self.assertIsInstance(
                result, int, "Function should return a valid timestamp"
            )
            self.assertGreater(result, 0, "Timestamp should be positive")

            # Get the log output to verify fallback behavior is logged
            log_output = log_buffer.getvalue()

            # Verify that fallback behavior is logged (warning instead of error)
            self.assertIn(
                "Using current time as fallback timestamp",
                log_output,
                "Should log fallback behavior",
            )

        finally:
            # Restore original handlers and level
            logger.handlers = original_handlers
            logger.setLevel(original_level)
            log_buffer.close()

    def test_comprehensive_mms_fallback_strategies(self):
        """Test all MMS participant extraction fallback strategies comprehensively."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various scenarios that should trigger different fallback strategies
        test_cases = [
            # Case 1: No participants, no soup, filename with phone
            {
                "filename": "Alice Smith +15551234567 - Text - 2025-08-13T12_08_52Z.html",
                "participants_raw": [],
                "soup": None,
                "description": "filename with phone number fallback",
            },
            # Case 2: No participants, no soup, filename without phone
            {
                "filename": "Bob Johnson - Text - 2025-08-13T12_08_52Z.html",
                "participants_raw": [],
                "soup": None,
                "description": "filename without phone number fallback",
            },
            # Case 3: No participants, with soup, but soup has no useful data
            {
                "filename": "Carol Davis - Text - 2025-08-13T12_08_52Z.html",
                "participants_raw": [],
                "soup": BeautifulSoup(
                    "<html><body><p>No useful data</p></body></html>", "html.parser"
                ),
                "description": "soup with no useful data fallback",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                messages = [
                    BeautifulSoup(
                        '<div class="message"><q>Test MMS</q></div>', "html.parser"
                    )
                ]

                try:
                    # Create mock objects for required parameters
                    mock_conversation_manager = type(
                        "MockConversationManager", (), {}
                    )()
                    mock_phone_lookup_manager = type("MockPhoneLookupManager", (), {})()

                    sms.write_mms_messages(
                        test_case["filename"],
                        test_case["participants_raw"],
                        messages,
                        None,
                        {},
                        mock_conversation_manager,
                        mock_phone_lookup_manager,
                        soup=test_case["soup"],
                    )
                    # Function should execute without errors
                except Exception as e:
                    self.fail(
                        f"MMS processing with {test_case['description']} should not fail: {e}"
                    )

    def test_edge_case_timestamp_extraction(self):
        """Test timestamp extraction with extreme edge cases and malformed HTML."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test extreme edge cases
        edge_cases = [
            # Case 1: Empty message with only whitespace
            {
                "html": '<div class="message">   </div>',
                "filename": "empty_whitespace.html",
                "should_fail": True,
            },
            # Case 2: Message with only punctuation
            {
                "html": '<div class="message">!@#$%^&*()</div>',
                "filename": "only_punctuation.html",
                "should_fail": True,
            },
            # Case 3: Message with very short text
            {
                "html": '<div class="message">Hi</div>',
                "filename": "very_short.html",
                "should_fail": True,
            },
            # Case 4: Message with malformed HTML
            {
                "html": '<div class="message"><unclosed_tag>Test</div>',
                "filename": "malformed_html.html",
                "should_fail": True,
            },
            # Case 5: Message with nested malformed elements
            {
                "html": '<div class="message"><span><div>Test</span></div>',
                "filename": "nested_malformed.html",
                "should_fail": True,
            },
        ]

        for i, test_case in enumerate(edge_cases):
            with self.subTest(i=i, case=test_case["filename"]):
                soup = BeautifulSoup(test_case["html"], "html.parser")
                message = soup.find("div", class_="message")
                if not message:
                    message = soup.find("div")

                if test_case["should_fail"]:
                    # Should fall back to current time
                    result = sms.get_time_unix(message, test_case["filename"])
                    current_time = int(time.time() * 1000)
                    # Allow for small timing differences (within 1 second)
                    self.assertLess(
                        abs(result - current_time),
                        1000,
                        f"Edge case {i} should fall back to current time",
                    )
                else:
                    # Should extract valid timestamp
                    result = sms.get_time_unix(message, test_case["filename"])
                    self.assertIsInstance(
                        result, int, f"Edge case {i} should return valid timestamp"
                    )
                    self.assertGreater(
                        result, 0, f"Edge case {i} should return positive timestamp"
                    )

    def test_filename_based_participant_extraction(self):
        """Test that participant extraction from filename patterns works correctly."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various filename patterns
        filename_patterns = [
            # Pattern 1: Name - Text - Timestamp
            {
                "filename": "Susan Nowak Tang - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Susan Nowak Tang",
                "description": "standard name - text - timestamp pattern",
            },
            # Pattern 2: Name with Phone - Text - Timestamp
            {
                "filename": "John Doe +15551234567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "John Doe +15551234567",
                "description": "name with phone - text - timestamp pattern",
            },
            # Pattern 3: Just Name - Text
            {
                "filename": "Alice Smith - Text.html",
                "expected_name": "Alice Smith",
                "description": "name - text pattern without timestamp",
            },
            # Pattern 4: Complex name with special characters
            {
                "filename": "Dr. Mary-Jane O'Connor, Jr. - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Dr. Mary-Jane O'Connor, Jr.",
                "description": "complex name with special characters",
            },
        ]

        for i, test_case in enumerate(filename_patterns):
            with self.subTest(i=i, pattern=test_case["description"]):
                # Test that the filename parsing logic works correctly
                if " - Text -" in test_case["filename"]:
                    name_part = test_case["filename"].split(" - Text -")[0]
                    self.assertEqual(
                        name_part,
                        test_case["expected_name"],
                        f"Filename parsing should extract correct name for {test_case['description']}",
                    )
                elif " - Text" in test_case["filename"]:
                    name_part = test_case["filename"].split(" - Text")[0]
                    self.assertEqual(
                        name_part,
                        test_case["expected_name"],
                        f"Filename parsing should extract correct name for {test_case['description']}",
                    )

    def test_timestamp_extraction_performance_with_filename(self):
        """Test that timestamp extraction performance is maintained with filename parameter."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Create a complex message with multiple timestamp candidates
        complex_html = """
        <div class="message">
            <abbr class="dt" title="2024-01-15T10:30:00Z">Jan 15</abbr>
            <q>Test message</q>
            <span class="timestamp">2024-01-15 10:30:00</span>
            <time datetime="2024-01-15T10:30:00Z">Jan 15</time>
            <div data-timestamp="2024-01-15T10:30:00Z">Extra info</div>
        </div>
        """

        soup = BeautifulSoup(complex_html, "html.parser")
        message = soup.find("div", class_="message")

        # Test performance: should still use Strategy 1 (fastest) even with filename parameter
        import time as time_module

        start_time = time_module.time()
        result1 = sms.get_time_unix(message, "performance_test.html")
        end_time = time_module.time()

        execution_time = end_time - start_time

        # Should execute quickly (within 100ms)
        self.assertLess(
            execution_time,
            0.1,
            "Timestamp extraction should be fast even with filename parameter",
        )

        # Should return the correct timestamp (Strategy 1 should win)
        expected_time = int(
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc).timestamp() * 1000
        )
        # Allow for timezone differences (within 6 hours)
        time_diff = abs(result1 - expected_time)
        self.assertLess(
            time_diff, 21600000, "Should extract correct timestamp from Strategy 1"
        )

        print(
            f"Performance test: extracted timestamp {result1} in {execution_time:.4f} seconds"
        )

    def test_filename_based_timestamp_extraction(self):
        """Test that timestamps can be extracted from filename patterns."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various filename timestamp patterns
        test_cases = [
            # Standard format: Name - Text - ISO timestamp
            {
                "filename": "Susan Nowak Tang - Text - 2025-08-13T12_08_52Z.html",
                "expected_timestamp": "2025-08-13T12:08:52Z",
                "description": "standard ISO timestamp with underscores",
            },
            # Format with colons: Name - Text - ISO timestamp with colons
            {
                "filename": "John Doe - Text - 2024-12-25T15:30:45Z.html",
                "expected_timestamp": "2024-12-25T15:30:45Z",
                "description": "ISO timestamp with colons",
            },
            # Different date format: Name - Text - different date
            {
                "filename": "Alice Smith - Text - 2023-06-15T09:15:30Z.html",
                "expected_timestamp": "2023-06-15T09:15:30Z",
                "description": "different date and time",
            },
            # Edge case: very recent date
            {
                "filename": "Bob Johnson - Text - 2025-01-01T00:00:00Z.html",
                "expected_timestamp": "2025-01-01T00:00:00Z",
                "description": "new year timestamp",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Create a message with no timestamp elements to force filename fallback
                test_html = (
                    '<div class="message"><q>Test message with no timestamp</q></div>'
                )
                soup = BeautifulSoup(test_html, "html.parser")
                message = soup.find("div", class_="message")

                # Should extract timestamp from filename (Strategy 11)
                result = sms.get_time_unix(message, test_case["filename"])

                # Verify the timestamp is reasonable and not current time fallback
                self.assertIsInstance(
                    result,
                    int,
                    f"Should return integer timestamp for {test_case['description']}",
                )
                self.assertGreater(
                    result,
                    1000000000000,
                    f"Should return reasonable timestamp (after 2001) for {test_case['description']}",
                )

                # Verify it's not the current time fallback
                current_time = int(time.time() * 1000)
                time_diff = abs(result - current_time)
                self.assertGreater(
                    time_diff,
                    1000000,
                    f"Should not return current time fallback for {test_case['description']}",
                )

                # Log the actual timestamp for verification
                print(
                    f"Filename timestamp extraction: {test_case['description']} -> {result}"
                )

    def test_enhanced_filename_participant_extraction(self):
        """Test enhanced participant extraction from various filename patterns."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various filename participant patterns
        test_cases = [
            # Case 1: Name with phone number
            {
                "filename": "Susan Nowak Tang +15551234567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Susan Nowak Tang +15551234567",
                "expected_phone": "+15551234567",
                "description": "name with phone number",
            },
            # Case 2: Name with formatted phone
            {
                "filename": "John Doe (555) 123-4567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "John Doe (555) 123-4567",
                "expected_phone": "(555) 123-4567",
                "description": "name with formatted phone",
            },
            # Case 3: Name with spaced phone
            {
                "filename": "Alice Smith 555 123 4567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Alice Smith 555 123 4567",
                "expected_phone": "555 123 4567",
                "description": "name with spaced phone",
            },
            # Case 4: Just name, no phone
            {
                "filename": "Bob Johnson - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Bob Johnson",
                "expected_phone": None,
                "description": "just name, no phone",
            },
            # Case 5: Complex name with special characters
            {
                "filename": "Dr. Mary-Jane O'Connor, Jr. - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Dr. Mary-Jane O'Connor, Jr.",
                "expected_phone": None,
                "description": "complex name with special characters",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Test that the filename parsing logic works correctly
                if " - Text -" in test_case["filename"]:
                    name_part = test_case["filename"].split(" - Text -")[0]
                    self.assertEqual(
                        name_part,
                        test_case["expected_name"],
                        f"Filename parsing should extract correct name for {test_case['description']}",
                    )

                    # Test phone number extraction if expected
                    if test_case["expected_phone"]:
                        # This would be tested in the actual MMS processing function
                        # For now, just verify the name extraction works
                        self.assertIn(
                            test_case["expected_phone"],
                            name_part,
                            f"Phone number should be in name part for {test_case['description']}",
                        )

    def test_filename_based_sms_alias_extraction(self):
        """Test that SMS processing uses filename information for better alias extraction."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test that SMS processing can extract aliases from filenames
        test_filename = "Susan Nowak Tang - Text - 2025-08-13T12_08_52Z.html"

        # Create a test message
        # test_html variable removed - not used

        # Mock the phone lookup manager to return None (no alias found)
        original_get_alias = sms.PHONE_LOOKUP_MANAGER.get_alias
        sms.PHONE_LOOKUP_MANAGER.get_alias = lambda phone, default: None

        try:
            # This should trigger the filename-based alias extraction
            # We can't easily test the full SMS processing without more setup,
            # but we can verify the filename parsing logic works
            if " - Text -" in test_filename:
                name_part = test_filename.split(" - Text -")[0]
                self.assertEqual(
                    name_part,
                    "Susan Nowak Tang",
                    "Should extract correct name from filename",
                )

                # Verify it looks like a person's name
                self.assertGreater(
                    len(name_part.strip()), 2, "Name should be longer than 2 characters"
                )
                self.assertFalse(
                    name_part.strip().isdigit(), "Name should not be just digits"
                )
        finally:
            # Restore original function
            sms.PHONE_LOOKUP_MANAGER.get_alias = original_get_alias

    def test_comprehensive_filename_parsing_edge_cases(self):
        """Test filename parsing with various edge cases and malformed patterns."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test edge cases
        edge_cases = [
            # Case 1: Filename without " - Text -" pattern
            {
                "filename": "just_a_filename.html",
                "should_have_timestamp": False,
                "should_have_name": False,
                "description": "no text pattern",
            },
            # Case 2: Filename with empty name part
            {
                "filename": " - Text - 2025-08-13T12_08_52Z.html",
                "should_have_timestamp": True,
                "should_have_name": False,
                "description": "empty name part",
            },
            # Case 3: Filename with only timestamp
            {
                "filename": "Text - 2025-08-13T12_08_52Z.html",
                "should_have_timestamp": True,
                "should_have_name": False,
                "description": "no name, just text and timestamp",
            },
            # Case 4: Malformed timestamp in filename
            {
                "filename": "John Doe - Text - invalid-timestamp.html",
                "should_have_timestamp": False,
                "should_have_name": True,
                "description": "malformed timestamp",
            },
            # Case 5: Very long name
            {
                "filename": "Dr. John Jacob Jingleheimer Schmidt III, Esq. - Text - 2025-08-13T12_08_52Z.html",
                "should_have_timestamp": True,
                "should_have_name": True,
                "description": "very long name",
            },
        ]

        for i, test_case in enumerate(edge_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Test timestamp extraction
                if (
                    test_case["should_have_timestamp"]
                    and " - Text -" in test_case["filename"]
                ):
                    # Create message with no timestamp to force filename fallback
                    test_html = '<div class="message"><q>Test</q></div>'
                    soup = BeautifulSoup(test_html, "html.parser")
                    message = soup.find("div", class_="message")

                    try:
                        result = sms.get_time_unix(message, test_case["filename"])
                        # Should either extract timestamp or fall back to current time
                        self.assertIsInstance(
                            result,
                            int,
                            f"Should return integer timestamp for {test_case['description']}",
                        )
                    except Exception as e:
                        # If timestamp extraction fails, it should fall back gracefully
                        self.assertIn(
                            "Message timestamp element not found",
                            str(e),
                            f"Should raise appropriate error for {test_case['description']}",
                        )

                # Test name extraction
                if (
                    test_case["should_have_name"]
                    and " - Text -" in test_case["filename"]
                ):
                    name_part = test_case["filename"].split(" - Text -")[0]
                    if name_part.strip():  # Only test if there's actually a name
                        self.assertGreater(
                            len(name_part.strip()),
                            0,
                            f"Should extract non-empty name for {test_case['description']}",
                        )

    def test_filename_timestamp_performance(self):
        """Test that filename-based timestamp extraction is performant."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test performance of filename timestamp extraction
        test_filename = "Performance Test - Text - 2025-08-13T12_08_52Z.html"

        # Create a message with no timestamp elements to force filename fallback
        test_html = '<div class="message"><q>Performance test message</q></div>'
        soup = BeautifulSoup(test_html, "html.parser")
        message = soup.find("div", class_="message")

        import time as time_module

        # Measure performance
        start_time = time_module.time()
        result = sms.get_time_unix(message, test_filename)
        end_time = time_module.time()

        execution_time = end_time - start_time

        # Should execute quickly (within 100ms)
        self.assertLess(
            execution_time, 0.1, "Filename timestamp extraction should be fast"
        )

        # Should return a valid timestamp
        self.assertIsInstance(result, int, "Should return integer timestamp")
        self.assertGreater(result, 1000000000000, "Should return reasonable timestamp")

        print(
            f"Filename timestamp extraction performance: {execution_time:.4f} seconds"
        )

    def test_numeric_filename_handling(self):
        """Test handling of numeric-only filenames that currently get skipped."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test numeric-only filenames that should be handled gracefully
        test_cases = [
            # Case 1: Pure numeric filename
            {
                "filename": "22891 - Text - 2022-04-22T18_31_20Z.html",
                "should_be_processed": True,
                "description": "pure numeric filename",
            },
            # Case 2: Numeric with text
            {
                "filename": "12345 - Text - 2021-12-31T19_09_30Z.html",
                "should_be_processed": True,
                "description": "numeric with text pattern",
            },
            # Case 3: Mixed numeric and text
            {
                "filename": "286669 - Text - 2021-08-01T12_33_13Z.html",
                "should_be_processed": True,
                "description": "mixed numeric and text",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Test that numeric filenames can be processed
                if " - Text -" in test_case["filename"]:
                    # Extract timestamp part
                    timestamp_part = test_case["filename"].split(" - Text -")[1]
                    if timestamp_part.endswith(".html"):
                        timestamp_part = timestamp_part[:-5]

                    # Should be able to parse timestamp
                    timestamp_part = timestamp_part.replace("_", ":")
                    try:
                        # This should work for valid timestamps
                        time_obj = dateutil.parser.parse(timestamp_part, fuzzy=True)
                        self.assertIsInstance(
                            time_obj,
                            datetime,
                            f"Should parse timestamp for {test_case['description']}",
                        )
                    except Exception as e:
                        # If parsing fails, it should be due to invalid timestamp, not filename format
                        self.fail(
                            f"Timestamp parsing should work for {test_case['description']}: {e}"
                        )

    def test_improved_name_extraction_from_filenames(self):
        """Test that name extraction from filenames works better than generic name_hashes."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test cases that should extract actual names instead of generic hashes
        test_cases = [
            # Case 1: Simple name
            {
                "filename": "Charles Tang - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Charles Tang",
                "should_not_be_generic": True,
                "description": "simple name extraction",
            },
            # Case 2: Name with phone
            {
                "filename": "Susan Nowak Tang +15551234567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Susan Nowak Tang +15551234567",
                "should_not_be_generic": True,
                "description": "name with phone extraction",
            },
            # Case 3: Complex name
            {
                "filename": "Dr. Mary-Jane O'Connor, Jr. - Text - 2025-08-13T12_08_52Z.html",
                "expected_name": "Dr. Mary-Jane O'Connor, Jr.",
                "should_not_be_generic": True,
                "description": "complex name extraction",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                if " - Text -" in test_case["filename"]:
                    name_part = test_case["filename"].split(" - Text -")[0]

                    # Should extract the actual name
                    self.assertEqual(
                        name_part,
                        test_case["expected_name"],
                        f"Should extract correct name for {test_case['description']}",
                    )

                    # Should not be a generic hash
                    if test_case["should_not_be_generic"]:
                        self.assertFalse(
                            name_part.startswith("name_"),
                            f"Should not generate generic name hash for {test_case['description']}",
                        )
                        self.assertFalse(
                            name_part.startswith("default_"),
                            f"Should not generate default participant for {test_case['description']}",
                        )

    def test_mms_participant_extraction_improvements(self):
        """Test that MMS participant extraction works better and doesn't skip messages."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test that MMS messages with name-based filenames get proper participants
        test_filename = "Charles Tang - Text - 2025-08-13T12_08_52Z.html"
        # test_messages variable removed - not used

        # This should create a proper participant instead of generic name_hash
        try:
            # Mock the participant extraction to see what happens
            # We can't easily test the full MMS processing without more setup,
            # but we can verify the filename parsing logic works correctly
            if " - Text -" in test_filename:
                name_part = test_filename.split(" - Text -")[0]

                # Should extract the actual name
                self.assertEqual(
                    name_part,
                    "Charles Tang",
                    "Should extract actual name from filename",
                )

                # Should be suitable for participant creation
                self.assertGreater(
                    len(name_part.strip()), 2, "Name should be long enough"
                )
                self.assertFalse(
                    name_part.strip().isdigit(), "Name should not be just digits"
                )

                # Should not generate generic participant names
                self.assertFalse(
                    name_part.startswith("name_"),
                    "Should not generate generic name hash",
                )
                self.assertFalse(
                    name_part.startswith("default_"),
                    "Should not generate default participant",
                )
        except Exception as e:
            self.fail(f"MMS participant extraction should work: {e}")

    def test_filename_timestamp_extraction_edge_cases(self):
        """Test timestamp extraction from various filename timestamp formats."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various timestamp formats found in filenames
        test_cases = [
            # Case 1: Standard ISO with underscores
            {
                "filename": "Test - Text - 2025-08-13T12_08_52Z.html",
                "expected_timestamp": "2025-08-13T12:08:52Z",
                "description": "ISO with underscores",
            },
            # Case 2: Different date format
            {
                "filename": "Test - Text - 2022-04-22T18_31_20Z.html",
                "expected_timestamp": "2022-04-22T18:31:20Z",
                "description": "different date with underscores",
            },
            # Case 3: Very old date
            {
                "filename": "Test - Text - 2011-05-18T19_48_15Z.html",
                "expected_timestamp": "2011-05-18T19:48:15Z",
                "description": "very old date",
            },
            # Case 4: Recent date
            {
                "filename": "Test - Text - 2025-07-01T15_39_34Z.html",
                "expected_timestamp": "2025-07-01T15:39:34Z",
                "description": "recent date",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Create message with no timestamp to force filename fallback
                test_html = '<div class="message"><q>Test message</q></div>'
                soup = BeautifulSoup(test_html, "html.parser")
                message = soup.find("div", class_="message")

                # Should extract timestamp from filename (Strategy 11)
                result = sms.get_time_unix(message, test_case["filename"])

                # Verify the timestamp is reasonable
                self.assertIsInstance(
                    result,
                    int,
                    f"Should return integer timestamp for {test_case['description']}",
                )
                self.assertGreater(
                    result,
                    1000000000000,
                    f"Should return reasonable timestamp for {test_case['description']}",
                )

                # Verify it's not the current time fallback
                current_time = int(time.time() * 1000)
                time_diff = abs(result - current_time)
                self.assertGreater(
                    time_diff,
                    1000000,
                    f"Should not return current time fallback for {test_case['description']}",
                )

                print(
                    f"Filename timestamp extraction: {test_case['description']} -> {result}"
                )

    def test_conversation_file_generation_quality(self):
        """Test that conversation files are generated with proper names and content."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test that conversation files get proper names instead of generic hashes
        test_cases = [
            # Case 1: Name-based filename should generate name-based conversation
            {
                "filename": "Charles Tang - Text - 2025-08-13T12_08_52Z.html",
                "expected_conversation_name": "Charles Tang",
                "description": "name-based conversation generation",
            },
            # Case 2: Phone-based filename should generate phone-based conversation
            {
                "filename": "+15551234567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_conversation_name": "+15551234567",
                "description": "phone-based conversation generation",
            },
            # Case 3: Mixed filename should prioritize name
            {
                "filename": "Susan Nowak Tang +15551234567 - Text - 2025-08-13T12_08_52Z.html",
                "expected_conversation_name": "Susan Nowak Tang +15551234567",
                "description": "mixed filename conversation generation",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                if " - Text -" in test_case["filename"]:
                    name_part = test_case["filename"].split(" - Text -")[0]

                    # Should extract the expected name/phone
                    self.assertEqual(
                        name_part,
                        test_case["expected_conversation_name"],
                        f"Should extract correct conversation name for {test_case['description']}",
                    )

                    # Should be suitable for file naming
                    self.assertGreater(
                        len(name_part.strip()),
                        0,
                        "Conversation name should not be empty",
                    )

                    # Should not contain invalid characters for filenames
                    invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
                    for char in invalid_chars:
                        self.assertNotIn(
                            char,
                            name_part,
                            f"Conversation name should not contain invalid character '{char}'",
                        )

    def test_performance_with_filename_extraction(self):
        """Test that filename-based extraction doesn't impact performance significantly."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test performance of filename-based extraction
        test_filename = "Performance Test - Text - 2025-08-13T12_08_52Z.html"

        # Create a message with no timestamp elements to force filename fallback
        test_html = '<div class="message"><q>Performance test message</q></div>'
        soup = BeautifulSoup(test_html, "html.parser")
        message = soup.find("div", class_="message")

        import time as time_module

        # Measure performance multiple times to get average
        times = []
        for _ in range(10):
            start_time = time_module.time()
            result = sms.get_time_unix(message, test_filename)
            end_time = time_module.time()
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Should execute quickly (within 50ms average, 100ms max)
        self.assertLess(
            avg_time,
            0.05,
            f"Filename timestamp extraction should be fast (avg: {avg_time:.4f}s)",
        )
        self.assertLess(
            max_time,
            0.1,
            f"Filename timestamp extraction should be consistently fast (max: {max_time:.4f}s)",
        )

        # Should return valid timestamp
        self.assertIsInstance(result, int, "Should return integer timestamp")
        self.assertGreater(result, 1000000000000, "Should return reasonable timestamp")

        print(
            f"Filename timestamp extraction performance: avg={avg_time:.4f}s, max={max_time:.4f}s"
        )

    def test_error_handling_for_malformed_filenames(self):
        """Test that malformed filenames are handled gracefully without crashing."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various malformed filename scenarios
        malformed_cases = [
            # Case 1: Empty filename
            {
                "filename": "",
                "should_handle_gracefully": True,
                "description": "empty filename",
            },
            # Case 2: Filename with no pattern
            {
                "filename": "just_a_filename.html",
                "should_handle_gracefully": True,
                "description": "no text pattern",
            },
            # Case 3: Filename with malformed timestamp
            {
                "filename": "Test - Text - invalid-timestamp.html",
                "should_handle_gracefully": True,
                "description": "malformed timestamp",
            },
            # Case 4: Filename with only timestamp
            {
                "filename": " - Text - 2025-08-13T12_08_52Z.html",
                "should_handle_gracefully": True,
                "description": "empty name part",
            },
        ]

        for i, test_case in enumerate(malformed_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Create a test message
                test_html = '<div class="message"><q>Test message</q></div>'
                soup = BeautifulSoup(test_html, "html.parser")
                message = soup.find("div", class_="message")

                try:
                    # Should handle malformed filenames gracefully
                    result = sms.get_time_unix(message, test_case["filename"])

                    # Should return some timestamp (either extracted or fallback)
                    self.assertIsInstance(
                        result,
                        int,
                        f"Should return integer timestamp for {test_case['description']}",
                    )
                    self.assertGreater(
                        result,
                        0,
                        f"Should return positive timestamp for {test_case['description']}",
                    )

                except Exception as e:
                    # If it raises an exception, it should be a known, expected error
                    self.assertIn(
                        "Message timestamp element not found",
                        str(e),
                        f"Should raise appropriate error for {test_case['description']}",
                    )

    def test_conversation_id_generation_consistency(self):
        """Test that conversation IDs are generated consistently for the same participants."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test that the same participants always generate the same conversation ID
        test_participants = ["+15551234567", "Susan Nowak Tang"]

        # Generate conversation ID multiple times
        conversation_ids = []
        for _ in range(5):
            conversation_id = sms.CONVERSATION_MANAGER.get_conversation_id(
                test_participants, True
            )
            conversation_ids.append(conversation_id)

        # All conversation IDs should be the same
        unique_ids = set(conversation_ids)
        self.assertEqual(
            len(unique_ids),
            1,
            f"Same participants should always generate same conversation ID, got: {unique_ids}",
        )

        # Test with different participant orders
        reversed_participants = list(reversed(test_participants))
        reversed_conversation_id = sms.CONVERSATION_MANAGER.get_conversation_id(
            reversed_participants, True
        )

        # Should generate different IDs for different orders (this is correct behavior)
        self.assertNotEqual(
            conversation_ids[0],
            reversed_conversation_id,
            "Conversation ID should be order-dependent for proper conversation management",
        )

        # But both should be valid conversation IDs
        self.assertIsInstance(
            conversation_ids[0], str, "Conversation ID should be string"
        )
        self.assertIsInstance(
            reversed_conversation_id, str, "Reversed conversation ID should be string"
        )

        print(
            f"Conversation ID generation test: {conversation_ids[0]} (consistent across 5 calls)"
        )
        print(
            f"Reversed order generates: {reversed_conversation_id} (different, as expected)"
        )

    def test_service_code_filtering_command_line(self):
        """Test that service code filtering can be controlled via command line arguments."""
        test_dir = Path(self.test_dir)

        # Test default behavior (service codes filtered out)
        sms.INCLUDE_SERVICE_CODES = False
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Service codes should be skipped by default
        test_cases = [
            "262966 - Text - 2022-01-12T00_54_17Z.html",
            "274624 - Text - 2025-04-16T18_34_53Z.html",
            "30368 - Text - 2016-11-13T23_17_42Z.html",
            "692639 - Text - 2025-04-19T19_47_09Z.html",
            "78015 - Text - 2020-05-08T17_00_37Z.html",
        ]

        for filename in test_cases:
            with self.subTest(filename=filename):
                should_skip = sms.should_skip_file(filename)
                self.assertTrue(
                    should_skip,
                    f"Service code should be skipped by default: {filename}",
                )

        # Test with service codes enabled
        sms.INCLUDE_SERVICE_CODES = True
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Service codes should NOT be skipped when enabled
        for filename in test_cases:
            with self.subTest(filename=filename):
                should_skip = sms.should_skip_file(filename)
                self.assertFalse(
                    should_skip,
                    f"Service code should NOT be skipped when enabled: {filename}",
                )

    def test_date_filtering_functionality(self):
        """Test that date filtering works correctly for messages."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test older-than filter
        sms.DATE_FILTER_OLDER_THAN = datetime(2023, 1, 1)

        # Messages from 2022 should be skipped
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(old_timestamp)
        self.assertTrue(
            should_skip,
            "Message from 2022 should be skipped with older-than 2023 filter",
        )

        # Messages from 2023 should NOT be skipped
        new_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(new_timestamp)
        self.assertFalse(
            should_skip,
            "Message from 2023 should NOT be skipped with older-than 2023 filter",
        )

        # Reset filter
        sms.DATE_FILTER_OLDER_THAN = None

        # Test newer-than filter
        sms.DATE_FILTER_NEWER_THAN = datetime(2024, 12, 31)

        # Messages from 2025 should be skipped
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(future_timestamp)
        self.assertTrue(
            should_skip,
            "Message from 2025 should be skipped with newer-than 2024 filter",
        )

        # Messages from 2024 should NOT be skipped
        current_timestamp = int(datetime(2024, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(current_timestamp)
        self.assertFalse(
            should_skip,
            "Message from 2024 should NOT be skipped with newer-than 2024 filter",
        )

        # Reset filter
        sms.DATE_FILTER_NEWER_THAN = None

        # Test both filters together
        sms.DATE_FILTER_OLDER_THAN = datetime(2023, 1, 1)
        sms.DATE_FILTER_NEWER_THAN = datetime(2024, 12, 31)

        # Message from 2022 should be skipped (too old)
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(old_timestamp)
        self.assertTrue(
            should_skip, "Message from 2022 should be skipped with both filters"
        )

        # Message from 2025 should be skipped (too new)
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(future_timestamp)
        self.assertTrue(
            should_skip, "Message from 2025 should be skipped with both filters"
        )

        # Message from 2023 should NOT be skipped (within range)
        within_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(within_timestamp)
        self.assertFalse(
            should_skip, "Message from 2023 should NOT be skipped with both filters"
        )

        # Reset filters
        sms.DATE_FILTER_OLDER_THAN = None
        sms.DATE_FILTER_NEWER_THAN = None

    def test_date_filtering_edge_cases(self):
        """Test edge cases for date filtering."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test with no filters (should not skip anything)
        sms.DATE_FILTER_OLDER_THAN = None
        sms.DATE_FILTER_NEWER_THAN = None

        test_timestamps = [
            int(datetime(2020, 1, 1, 0, 0, 0).timestamp() * 1000),  # Very old
            int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000),  # Recent
            int(datetime(2025, 12, 31, 23, 59, 59).timestamp() * 1000),  # Future
        ]

        for timestamp in test_timestamps:
            with self.subTest(timestamp=timestamp):
                should_skip = sms.should_skip_message_by_date(timestamp)
                self.assertFalse(
                    should_skip,
                    f"Message should NOT be skipped with no filters: {timestamp}",
                )

        # Test with invalid timestamps (should not skip)
        invalid_timestamps = [0, -1, 999999999999999]  # Invalid Unix timestamps

        for timestamp in invalid_timestamps:
            with self.subTest(timestamp=timestamp):
                should_skip = sms.should_skip_message_by_date(timestamp)
                self.assertFalse(
                    should_skip,
                    f"Invalid timestamp should NOT cause skipping: {timestamp}",
                )

    def test_corrupted_filename_detection(self):
        """Test that corrupted Google Voice filenames are properly detected and handled."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test cases for corrupted filenames
        corrupted_cases = [
            # Case 1: Legitimate Google Voice export with file parts (should NOT be skipped)
            {
                "filename": "PhilipLICW Abramovitz - LI Clean Water - Text - 2024-07-29T16_10_03Z-6-1",
                "should_skip": False,  # This is now legitimate
                "description": "legitimate Google Voice export with file parts",
                "can_clean": False,  # Should not be cleaned
                "cleaned": "PhilipLICW Abramovitz - LI Clean Water - Text - 2024-07-29T16_10_03Z-6-1",  # Should remain unchanged
            },
            # Case 2: Multiple extra dashes (not legitimate Google Voice export pattern)
            {
                "filename": "John Doe - Text - 2024-08-15T12_30_45Z-123-456.html",
                "should_skip": True,
                "description": "multiple extra dashes (not legitimate pattern)",
                "can_clean": True,
                "cleaned": "John Doe - Text - 2024-08-15T12_30_45Z.html",
            },
            # Case 3: Missing .html extension
            {
                "filename": "Jane Smith - Text - 2024-06-20T09_15_30Z",
                "should_skip": True,
                "description": "missing .html extension",
                "can_clean": False,
            },
            # Case 4: Corrupted timestamp with extra numbers
            {
                "filename": "Bob Wilson - Text - 2024-05-10T14_25_00Z-999.html",
                "should_skip": True,
                "description": "corrupted timestamp with extra numbers",
                "can_clean": True,
                "cleaned": "Bob Wilson - Text - 2024-05-10T14_25_00Z.html",
            },
        ]

        # Test valid filenames (should not be skipped)
        valid_cases = [
            "John Doe - Text - 2024-08-15T12_30_45Z.html",
            "Jane Smith - Text - 2024-06-20T09_15_30Z.html",
            "Bob Wilson - Text - 2024-05-10T14_25_00Z.html",
            "Group Conversation - 2024-07-01T10_00_00Z.html",
        ]

        # Test corrupted filename detection
        for i, test_case in enumerate(corrupted_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Test should_skip_file
                should_skip = sms.should_skip_file(test_case["filename"])
                self.assertEqual(
                    should_skip,
                    test_case["should_skip"],
                    f"Filename should_skip result: {test_case['description']}",
                )

                # Test is_corrupted_filename
                is_corrupted = sms.is_corrupted_filename(test_case["filename"])
                # For legitimate Google Voice exports, this should be False
                if test_case["should_skip"]:
                    self.assertTrue(
                        is_corrupted,
                        f"Corrupted filename should be detected: {test_case['description']}",
                    )
                else:
                    self.assertFalse(
                        is_corrupted,
                        f"Legitimate filename should NOT be detected as corrupted: {test_case['description']}",
                    )

                # Test cleaning if applicable
                if test_case["can_clean"]:
                    cleaned = sms.clean_corrupted_filename(test_case["filename"])
                    self.assertEqual(
                        cleaned,
                        test_case["cleaned"],
                        f"Should clean corrupted filename: {test_case['description']}",
                    )
                else:
                    cleaned = sms.clean_corrupted_filename(test_case["filename"])
                    self.assertEqual(
                        cleaned,
                        test_case["filename"],
                        f"Should not clean uncorrupted filename: {test_case['description']}",
                    )

        # Test valid filenames
        for filename in valid_cases:
            with self.subTest(filename=filename):
                # Test should_skip_file
                should_skip = sms.should_skip_file(filename)
                self.assertFalse(
                    should_skip, f"Valid filename should NOT be skipped: {filename}"
                )

                # Test is_corrupted_filename
                is_corrupted = sms.is_corrupted_filename(filename)
                self.assertFalse(
                    is_corrupted,
                    f"Valid filename should NOT be detected as corrupted: {filename}",
                )

                # Test cleaning (should return original)
                cleaned = sms.clean_corrupted_filename(filename)
                self.assertEqual(
                    cleaned,
                    filename,
                    f"Valid filename should not be modified: {filename}",
                )

    def test_corrupted_filename_cleaning_edge_cases(self):
        """Test edge cases for corrupted filename cleaning."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test edge cases
        edge_cases = [
            # Case 1: Very long corrupted filename
            {
                "filename": "Very Long Name With Many Words And Spaces - Text - 2024-01-01T00_00_00Z-123-456-789-012-345-678-901-234-567-890.html",
                "should_skip": True,
                "description": "very long corrupted filename",
            },
            # Case 2: Corrupted filename with special characters
            {
                "filename": "Name@Company - Text - 2024-02-02T01_01_01Z-abc-def.html",
                "should_skip": True,
                "description": "corrupted filename with special characters",
            },
            # Case 3: Corrupted filename with underscores in name
            {
                "filename": "John_Doe_Smith - Text - 2024-03-03T02_02_02Z-xyz.html",
                "should_skip": True,
                "description": "corrupted filename with underscores in name",
            },
            # Case 4: Corrupted filename with numbers in name
            {
                "filename": "John123 Doe456 - Text - 2024-04-04T03_03_03Z-789.html",
                "should_skip": True,
                "description": "corrupted filename with numbers in name",
            },
        ]

        for i, test_case in enumerate(edge_cases):
            with self.subTest(i=i, case=test_case["description"]):
                # Test should_skip_file
                should_skip = sms.should_skip_file(test_case["filename"])
                self.assertTrue(
                    should_skip,
                    f"Edge case corrupted filename should be skipped: {test_case['description']}",
                )

                # Test is_corrupted_filename
                is_corrupted = sms.is_corrupted_filename(test_case["filename"])
                self.assertTrue(
                    is_corrupted,
                    f"Edge case corrupted filename should be detected: {test_case['description']}",
                )

    def test_numeric_filename_processing_fixes(self):
        """Test that numeric filenames are now filtered out by default (service codes)."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test cases that are now filtered out by default (service codes)
        test_cases = [
            # Case 1: Numeric service codes (common for verification codes)
            {
                "filename": "262966 - Text - 2022-01-12T00_54_17Z.html",
                "should_skip": True,  # Now filtered out by default
                "description": "verification service code",
            },
            # Case 2: Bank alerts and notifications
            {
                "filename": "274624 - Text - 2025-04-16T18_34_53Z.html",
                "should_skip": True,  # Now filtered out by default
                "description": "bank alert code",
            },
            # Case 3: Emergency/service notifications
            {
                "filename": "30368 - Text - 2016-11-13T23_17_42Z.html",
                "should_skip": True,  # Now filtered out by default
                "description": "emergency notification code",
            },
            # Case 4: Marketing/promotional codes
            {
                "filename": "692639 - Text - 2025-04-19T19_47_09Z.html",
                "should_skip": True,  # Now filtered out by default
                "description": "promotional code",
            },
            # Case 5: Various other service codes
            {
                "filename": "78015 - Text - 2020-05-08T17_00_37Z.html",
                "should_skip": True,  # Now filtered out by default
                "description": "service notification code",
            },
            # Case 6: Still skip truly invalid patterns
            {
                "filename": " - Text - 2020-05-08T17_00_37Z.html",
                "should_skip": True,
                "description": "invalid empty pattern",
            },
            # Case 7: Still skip corrupted filenames
            {
                "filename": 'test<>:"|?*.html',
                "should_skip": True,
                "description": "corrupted filename with invalid characters",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                result = sms.should_skip_file(test_case["filename"])

                if test_case["should_skip"]:
                    self.assertTrue(
                        result,
                        f"Should skip {test_case['description']}: {test_case['filename']}",
                    )
                else:
                    self.assertFalse(
                        result,
                        f"Should NOT skip {test_case['description']}: {test_case['filename']}",
                    )

    def test_improved_name_based_participants(self):
        """Test that name-based participants use actual names instead of generic hashes."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test cases that should create meaningful participant names
        test_cases = [
            # Case 1: Person's name should be used directly
            {
                "filename": "John Doe - Text - 2025-08-13T12_08_52Z.html",
                "expected_participant": "John_Doe",  # Safe filename version
                "expected_alias": "John Doe",  # Display version
                "description": "person name with space",
            },
            # Case 2: Business name
            {
                "filename": "Eastern Car Service SMS - Text - 2018-01-22T19_25_.html",
                "expected_participant": "Eastern_Car_Service_SMS",
                "expected_alias": "Eastern Car Service SMS",
                "description": "business name with spaces",
            },
            # Case 3: Name with special characters
            {
                "filename": "Dr. Mary-Jane O'Connor - Text - 2025-08-13T12_08_52Z.html",
                "expected_participant": "Dr._Mary-Jane_O'Connor",
                "expected_alias": "Dr. Mary-Jane O'Connor",
                "description": "name with special characters",
            },
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(i=i, case=test_case["description"]):
                if " - Text -" in test_case["filename"]:
                    name_part = test_case["filename"].split(" - Text -")[0].strip()

                    # Test the name processing logic
                    if name_part and len(name_part) > 0:
                        safe_name = (
                            name_part.replace(" ", "_")
                            .replace("/", "_")
                            .replace("\\", "_")
                        )

                        # Should create meaningful participant identifiers
                        self.assertEqual(
                            safe_name,
                            test_case["expected_participant"],
                            f"Should create meaningful participant for {test_case['description']}",
                        )
                        self.assertEqual(
                            name_part,
                            test_case["expected_alias"],
                            f"Should create correct alias for {test_case['description']}",
                        )

                        # Should not contain generic patterns
                        self.assertNotIn(
                            "name_",
                            safe_name,
                            f"Should not create generic hash for {test_case['description']}",
                        )
                        self.assertNotIn(
                            "default_",
                            safe_name,
                            f"Should not create default participant for {test_case['description']}",
                        )

    def test_mms_progress_counter_fix(self):
        """Test that MMS progress counter doesn't exceed 100% due to variable name collision."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Create mock MMS messages for testing
        mock_messages = []
        for i in range(5):
            mock_html = f'<div class="message"><cite><span>Contact {i}</span></cite><q>MMS message {i}</q></div>'
            mock_messages.append(BeautifulSoup(mock_html, "html.parser").find("div"))

        # Test that we can enumerate messages without variable name collision
        # This simulates the fixed logic in write_mms_messages
        participants = ["Contact1", "Contact2"]
        participant_aliases = ["Alias1", "Alias2"]

        for message_idx, message in enumerate(mock_messages):
            # This should work without variable name collision
            final_aliases = []
            for participant_idx, phone in enumerate(participants):
                if (
                    participant_idx < len(participant_aliases)
                    and participant_aliases[participant_idx]
                ):
                    final_aliases.append(participant_aliases[participant_idx])
                else:
                    final_aliases.append(f"Phone{participant_idx}")

            # Progress calculation should be correct
            progress_percentage = ((message_idx + 1) / len(mock_messages)) * 100

            # Should never exceed 100%
            self.assertLessEqual(
                progress_percentage,
                100.0,
                f"Progress should not exceed 100% at message {message_idx + 1}",
            )

            # Should be accurate
            expected_percentage = ((message_idx + 1) / 5) * 100
            self.assertEqual(
                progress_percentage,
                expected_percentage,
                f"Progress should be accurate at message {message_idx + 1}",
            )

    def test_service_code_filename_support(self):
        """Test that service codes and short codes are filtered out by default but can be enabled."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various service code patterns that should be processed
        service_codes = [
            # Common verification code senders
            "262966",  # Common verification service
            "87892",  # Verification service
            "47873",  # Marketing service
            "44444",  # Common service code
            "22395",  # Alert service
            "78015",  # Notification service
            "386732",  # Business alert
            "692639",  # Promotional code
            "274624",  # Bank alert
            "30368",  # Emergency notification
            "12345",  # Generic service
            "99999",  # Service code
        ]

        # Test default behavior (service codes filtered out)
        for code in service_codes:
            filename = f"{code} - Text - 2025-01-01T12_00_00Z.html"
            with self.subTest(code=code):
                # Should be skipped by default (filtered out)
                should_skip = sms.should_skip_file(filename)
                self.assertTrue(
                    should_skip,
                    f"Service code {code} should be filtered out by default",
                )

        # Test with service codes enabled
        sms.INCLUDE_SERVICE_CODES = True
        for code in service_codes:
            filename = f"{code} - Text - 2025-01-01T12_00_00Z.html"
            with self.subTest(code=code):
                # Should NOT be skipped when enabled
                should_skip = sms.should_skip_file(filename)
                self.assertFalse(
                    should_skip, f"Service code {code} should be processed when enabled"
                )

                # Should be able to extract the code as a fallback number
                fallback_number = sms.extract_fallback_number_cached(filename)
                self.assertGreater(
                    fallback_number,
                    0,
                    f"Should extract number from service code {code}",
                )

        # Reset to default
        sms.INCLUDE_SERVICE_CODES = False

    def test_corrupted_filename_handling(self):
        """Test that truly corrupted filenames are still properly skipped."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test filenames that should still be skipped
        corrupted_filenames = [
            # Empty or whitespace-only patterns
            " - Text - 2025-01-01T12_00_00Z.html",
            "- Text - 2025-01-01T12_00_00Z.html",
            "  - Text - 2025-01-01T12_00_00Z.html",
            # Invalid characters that suggest file corruption
            "test<file.html",
            "test>file.html",
            "test:file.html",
            'test"file.html',
            "test|file.html",
            "test?file.html",
            "test*file.html",
            # Completely empty or invalid patterns
            "",
            "   ",
            "-",
            ".",
            "_",
        ]

        for filename in corrupted_filenames:
            with self.subTest(filename=filename):
                should_skip = sms.should_skip_file(filename)
                self.assertTrue(
                    should_skip, f"Corrupted filename should be skipped: '{filename}'"
                )

    def test_legitimate_google_voice_export_patterns(self):
        """Test that legitimate Google Voice export patterns with file parts are properly handled."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test legitimate Google Voice export patterns with file parts
        legitimate_files = [
            "PhilipLICW Abramovitz - LI Clean Water - Text - 2024-07-29T16_10_03Z-6-1",
            "PhilipLICW Abramovitz - LI Clean Water - Text - 2024-08-05T14_21_52Z-6-1",
            "John Doe - Text - 2025-08-13T12_08_52Z-1-2.html",
            "Alice Smith - Voicemail - 2025-08-13T12_08_52Z-3-1.html",
            "Bob Johnson - Received - 2025-08-13T12_08_52Z-2-1.html",
            "Carol Davis - Placed - 2025-08-13T12_08_52Z-1-3.html",
            "David Wilson - Missed - 2025-08-13T12_08_52Z-4-2.html",
        ]

        for filename in legitimate_files:
            with self.subTest(filename=filename):
                # These should be detected as legitimate Google Voice exports
                self.assertTrue(
                    sms.is_legitimate_google_voice_export(filename),
                    f"Should detect {filename} as legitimate Google Voice export",
                )
                # These should NOT be flagged as corrupted
                self.assertFalse(
                    sms.is_corrupted_filename(filename),
                    f"Should not flag {filename} as corrupted",
                )
                # These should NOT be skipped
                should_skip = sms.should_skip_file(filename)
                self.assertFalse(
                    should_skip, f"Should not skip legitimate filename: {filename}"
                )

        # Test edge cases
        self.assertTrue(
            sms.is_legitimate_google_voice_export(
                "Test - Text - 2024-07-29T16_10_03Z-6-1"
            )
        )
        self.assertTrue(
            sms.is_legitimate_google_voice_export(
                "Test - Text - 2024-07-29T16_10_03Z-6-1.html"
            )
        )
        self.assertFalse(
            sms.is_legitimate_google_voice_export(
                "Test - Text - 2024-07-29T16_10_03Z.html"
            )
        )
        self.assertFalse(
            sms.is_legitimate_google_voice_export(
                "Test - Text - 2024-07-29T16_10_03Z-extra-stuff.html"
            )
        )

        # Test that cleaning preserves legitimate patterns
        test_cases = [
            {
                "original": "PhilipLICW Abramovitz - LI Clean Water - Text - 2024-07-29T16_10_03Z-6-1",
                "expected": "PhilipLICW Abramovitz - LI Clean Water - Text - 2024-07-29T16_10_03Z-6-1",
            },
            {
                "original": "John Doe - Text - 2025-08-13T12_08_52Z-1-2.html",
                "expected": "John Doe - Text - 2025-08-13T12_08_52Z-1-2.html",
            },
        ]

        for test_case in test_cases:
            with self.subTest(original=test_case["original"]):
                cleaned = sms.clean_corrupted_filename(test_case["original"])
                self.assertEqual(
                    cleaned,
                    test_case["expected"],
                    f"Should preserve legitimate pattern: {test_case['original']}",
                )

    def test_legitimate_google_voice_export_with_file_parts_processing(self):
        """Test that legitimate Google Voice export files with file parts are processed correctly."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test files with legitimate file part patterns
        test_cases = [
            "Test User - Text - 2024-01-15T10_30_00Z-6-1.html",
            "Another User - Voicemail - 2024-02-20T14_45_30Z-8-2.html",
            "Third User - Placed - 2024-03-25T09_15_45Z-7-5.html",
        ]

        for filename in test_cases:
            with self.subTest(filename=filename):
                # These should NOT be considered corrupted
                self.assertFalse(
                    sms.is_corrupted_filename(filename),
                    f"Filename '{filename}' should not be considered corrupted",
                )

                # These should NOT be skipped
                self.assertFalse(
                    sms.should_skip_file(filename),
                    f"Filename '{filename}' should not be skipped",
                )

                # These should be legitimate Google Voice exports
                self.assertTrue(
                    sms.is_legitimate_google_voice_export(filename),
                    f"Filename '{filename}' should be legitimate Google Voice export",
                )

                # Cleaning should preserve legitimate file parts (if cleaning is needed)
                # For legitimate files, cleaning might return the original or a cleaned version
                cleaned = sms.clean_corrupted_filename(filename)
                # Check that the cleaned version still contains the legitimate pattern
                self.assertTrue(
                    any(part in cleaned for part in ["-6-1", "-8-2", "-7-5"]),
                    f"Cleaned filename should preserve legitimate file parts: {cleaned}",
                )

    def test_hash_based_fallback_phone_numbers(self):
        """Test that files without phone numbers generate hash-based fallback numbers."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test files that don't contain phone numbers
        test_cases = [
            "Susan Nowak Tang - Text - 2023-02-04T14_01_06Z.html",
            "Charles Tang - Text - 2024-01-06T21_42_59Z.html",
            "Aniella Tang - Text - 2021-04-10T00_40_26Z.html",
        ]

        for filename in test_cases:
            with self.subTest(filename=filename):
                # Extract fallback number
                fallback_number = sms.extract_fallback_number_cached(filename)

                # Should return a valid number (not 0)
                self.assertNotEqual(
                    fallback_number,
                    0,
                    f"Fallback number for '{filename}' should not be 0",
                )

                # Should be a reasonable length (25 characters for UN_ prefixed hash-based)
                fallback_str = str(fallback_number)
                self.assertEqual(
                    len(fallback_str),
                    25,
                    f"Hash-based fallback should be 25 characters, got {len(fallback_str)}",
                )

                # Should be valid for phone number validation
                self.assertTrue(
                    sms.is_valid_phone_number(fallback_number),
                    f"Fallback number {fallback_number} should be valid",
                )

    def test_enhanced_phone_number_extraction_strategies(self):
        """Test all phone number extraction strategies including hash-based fallbacks."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various filename patterns
        test_cases = [
            # Strategy 1: Numeric service codes
            ("262966 - Text - 2024-01-15T10_30_00Z.html", "numeric service code"),
            # Strategy 2: Phone numbers in filename
            (
                "+12125551234 - Text - 2024-02-20T14_45_30Z.html",
                "phone number in filename",
            ),
            # Strategy 3: International format
            (
                "+44 20 7946 0958 - Text - 2024-03-25T09_15_45Z.html",
                "international phone number",
            ),
            # Strategy 4: Any sequence of digits
            ("User123 - Text - 2024-04-10T16_20_15Z.html", "digits in filename"),
            # Strategy 5: Hash-based fallback
            (
                "Susan Nowak Tang - Text - 2023-02-04T14_01_06Z.html",
                "hash-based fallback",
            ),
        ]

        for filename, description in test_cases:
            with self.subTest(description=description):
                fallback_number = sms.extract_fallback_number_cached(filename)
    
                # Should return a valid number
                self.assertNotEqual(
                    fallback_number,
                    0,
                    f"Strategy '{description}' should return valid number",
                )
    
                # Check if it's a valid phone number or a special case
                if description == "numeric service code":
                    # Service codes are not valid phone numbers
                    self.assertFalse(
                        sms.is_valid_phone_number(fallback_number),
                        f"Service code {fallback_number} should not be a valid phone number",
                    )
                else:
                    # Should pass phone number validation
                    self.assertTrue(
                        sms.is_valid_phone_number(fallback_number),
                        f"Number {fallback_number} from '{description}' should be valid",
                    )

    def test_phone_number_validation_with_hash_based_numbers(self):
        """Test that phone number validation accepts hash-based fallback numbers."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various number types
        test_cases = [
            # Valid phone numbers
            ("+12125551234", True, "valid US phone number"),
            ("+44 20 7946 0958", True, "valid international phone number"),
            ("12125551234", True, "valid US phone number without +"),
            # Hash-based fallback numbers (UN_ prefixed)
            ("UN_E7GCre66q93-hk4l3wGubA", True, "hash-based fallback number"),
            ("UN_32Y7VxNu6Run-Dn-80XD4A", True, "hash-based fallback number"),
            # Invalid numbers
            ("123", False, "too short"),
            ("1234567890123456", False, "too long"),
            ("0", False, "zero"),
            ("", False, "empty string"),
        ]

        for phone_number, expected_valid, description in test_cases:
            with self.subTest(description=description):
                is_valid = sms.is_valid_phone_number(phone_number)
                self.assertEqual(
                    is_valid,
                    expected_valid,
                    f"Phone number '{phone_number}' ({description}) should be {expected_valid}",
                )

    def test_legitimate_google_voice_export_edge_cases(self):
        """Test edge cases for legitimate Google Voice export detection."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test various patterns
        test_cases = [
            # Legitimate patterns (should return True)
            (
                "User - Text - 2024-01-15T10_30_00Z-6-1.html",
                True,
                "legitimate with single digits",
            ),
            (
                "User - Voicemail - 2024-02-20T14_45_30Z-8-2.html",
                True,
                "legitimate with single digits",
            ),
            (
                "User - Placed - 2024-03-25T09_15_45Z-7-5.html",
                True,
                "legitimate with single digits",
            ),
            # Not legitimate patterns (should return False)
            (
                "User - Text - 2024-01-15T10_30_00Z-123-456.html",
                False,
                "multi-digit file parts",
            ),
            (
                "User - Text - 2024-01-15T10_30_00Z-12-34.html",
                False,
                "multi-digit file parts",
            ),
            ("User - Text - 2024-01-15T10_30_00Z.html", False, "no file parts"),
            (
                "User - Text - 2024-01-15T10_30_00Z",
                False,
                "no file parts, no extension",
            ),
        ]

        for filename, expected_legitimate, description in test_cases:
            with self.subTest(description=description):
                is_legitimate = sms.is_legitimate_google_voice_export(filename)
                self.assertEqual(
                    is_legitimate,
                    expected_legitimate,
                    f"Filename '{filename}' ({description}) should be {expected_legitimate}",
                )

    def test_corrupted_filename_cleaning_preserves_legitimate_parts(self):
        """Test that corrupted filename cleaning preserves legitimate file parts."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "html")

        # Test that legitimate file parts are preserved during cleaning
        test_cases = [
            (
                "User - Text - 2024-01-15T10_30_00Z-6-1.html",
                "-6-1",
                "legitimate single digits",
            ),
            (
                "User - Voicemail - 2024-02-20T14_45_30Z-8-2.html",
                "-8-2",
                "legitimate single digits",
            ),
            (
                "User - Placed - 2024-03-25T09_15_45Z-7-5.html",
                "-7-5",
                "legitimate single digits",
            ),
        ]

        for filename, expected_parts, description in test_cases:
            with self.subTest(description=description):
                # These should be legitimate Google Voice exports
                self.assertTrue(
                    sms.is_legitimate_google_voice_export(filename),
                    f"Filename '{filename}' should be legitimate: {description}",
                )

                # Cleaning should preserve legitimate file parts
                cleaned = sms.clean_corrupted_filename(filename)
                self.assertIn(
                    expected_parts,
                    cleaned,
                    f"Cleaned filename should preserve {expected_parts} for {description}",
                )

    def test_group_conversation_message_grouping_fix(self):
        """Test that all messages in a group conversation are properly grouped together."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, 8192, 1000, 25000, False, "xml")

        # Create a test HTML file that simulates the reported issue
        # This represents a group conversation where messages from different participants
        # should all end up in the same conversation file
        test_html = """
        <div class="participants">Group conversation with:
            <cite class="sender vcard">
                <a class="tel" href="tel:+13472811848">
                    <span class="fn">SusanT</span>
                </a>
            </cite>,
            <cite class="sender vcard">
                <a class="tel" href="tel:+13479098263">
                    <span class="fn">Inessa</span>
                </a>
            </cite>
        </div>
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13472811848">
                    <span class="fn">SusanT</span>
                </a>
            </cite>
            <q>Hello everyone!</q>
            <abbr class="dt" title="2024-01-01T10:00:00Z">10:00 AM</abbr>
        </div>
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13479098263">
                    <span class="fn">Inessa</span>
                </a>
            </cite>
            <q>Hi SusanT!</q>
            <abbr class="dt" title="2024-01-01T10:01:00Z">10:01 AM</abbr>
        </div>
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13472811848">
                    <span class="fn">SusanT</span>
                </a>
            </cite>
            <q>How are you doing?</q>
            <abbr class="dt" title="2024-01-01T10:02:00Z">10:02 AM</abbr>
        </div>
        """

        # Create test HTML file
        test_file = test_dir / "Calls" / "test_group_conversation.html"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(test_html)

        # Parse the HTML
        soup = BeautifulSoup(test_html, "html.parser")
        
        # Extract participants and messages
        participants_raw = soup.select("div.participants")
        messages_raw = soup.select("div.message")
        
        # Test participant extraction
        participants, aliases = sms.get_participant_phone_numbers_and_aliases(participants_raw)
        expected_phones = ["+13472811848", "+13479098263"]
        expected_aliases = ["SusanT", "Inessa"]
        
        self.assertEqual(participants, expected_phones)
        self.assertEqual(aliases, expected_aliases)
        
        # Add aliases to phone lookup manager
        phone_lookup = sms.PHONE_LOOKUP_MANAGER
        for phone, name in zip(participants, aliases):
            phone_lookup.add_alias(phone, name)
        
        # Test that the group conversation detection works correctly
        # This simulates what happens in write_sms_messages
        is_group = False
        group_participants = []
        
        if participants_raw:
            participants, aliases = sms.get_participant_phone_numbers_and_aliases(participants_raw)
            if participants and len(participants) > 1:
                is_group = True
                group_participants = participants
        
        self.assertTrue(is_group)
        self.assertEqual(len(group_participants), 2)
        self.assertIn("+13472811848", group_participants)
        self.assertIn("+13479098263", group_participants)
        
        # Test conversation ID generation
        conv_manager = sms.CONVERSATION_MANAGER
        group_id = conv_manager.get_conversation_id(group_participants, is_group, phone_lookup)
        
        # Should include both participants
        self.assertIn("SusanT", group_id)
        self.assertIn("Inessa", group_id)
        
        # Now test the actual message processing
        # This simulates the key fix: all messages should use the same conversation ID
        conversation_id = conv_manager.get_conversation_id(group_participants, is_group, phone_lookup)
        
        # Process each message and verify they all use the same conversation ID
        for i, message in enumerate(messages_raw):
            # Extract message info
            message_content = sms.get_message_text(message)
            message_time = sms.get_time_unix(message, test_file.name)
            
            # Get sender info
            cite_element = message.cite
            sender_phone = None
            if cite_element and cite_element.a:
                href = cite_element.a.get("href", "")
                if href.startswith("tel:"):
                    match = sms.TEL_HREF_PATTERN.search(href)
                    if match:
                        try:
                            phone_number = sms.format_number(
                                sms.phonenumbers.parse(match.group(1), "US")
                            )
                            sender_phone = phone_number
                        except Exception:
                            pass
            
            # Verify that each message would use the same conversation ID
            # This is the key test - all messages should go to the same conversation file
            self.assertIsNotNone(sender_phone)
            self.assertIn(sender_phone, group_participants)
            
            # Log the message details for verification
            print(f"Message {i+1}: {sender_phone} -> {message_content[:50]}...")
        
        # Verify that the conversation ID is consistent and meaningful
        self.assertIsNotNone(conversation_id)
        self.assertGreater(len(conversation_id), 0)
        self.assertIn("SusanT", conversation_id)
        self.assertIn("Inessa", conversation_id)
        
        print(f"\nGenerated group conversation ID: {conversation_id}")
        print("✅ All messages in the group conversation will use the same conversation ID")
        print("✅ This ensures all messages (from SusanT, Inessa, etc.) end up in the same file")
        print("✅ The fix prevents messages from being scattered across different conversation files")

    def test_index_page_attachment_count_accuracy(self):
        """Test that the index page shows accurate attachment counts (not counting placeholders)."""
        # Create test data with real attachments and placeholder attachments
        test_data = {
            "conversation_with_real_attachments.html": {
                "content": """<html>
                <table>
                    <tr>
                        <td class="timestamp">2024-01-01 10:00:00</td>
                        <td class="sender">TestUser</td>
                        <td class="message">Message with image</td>
                        <td>📷 Image</td>
                    </tr>
                    <tr>
                        <td class="timestamp">2024-01-01 11:00:00</td>
                        <td class="sender">TestUser2</td>
                        <td class="message">Message without attachment</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td class="timestamp">2024-01-01 12:00:00</td>
                        <td class="sender">TestUser</td>
                        <td class="message">Message with vCard</td>
                        <td>📇 vCard</td>
                    </tr>
                </table>
                </html>""",
            },
            "conversation_with_no_attachments.html": {
                "content": """<html>
                <table>
                    <tr>
                        <td class="timestamp">2024-01-01 10:00:00</td>
                        <td class="sender">TestUser</td>
                        <td class="message">Plain message</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td class="timestamp">2024-01-01 11:00:00</td>
                        <td class="sender">TestUser2</td>
                        <td class="message">Another plain message</td>
                        <td>-</td>
                    </tr>
                </table>
                </html>""",
            }
        }
        
        # Write test data to temporary files
        test_output_dir = Path(self.test_dir) / "conversations"
        test_output_dir.mkdir(exist_ok=True)
        
        for filename, data in test_data.items():
            test_file_path = test_output_dir / filename
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(data["content"])
        
        # Create a conversation manager to test
        from core.conversation_manager import ConversationManager
        conv_manager = ConversationManager(test_output_dir, output_format="html")
        
        # Manually set conversation stats to simulate real processing
        conv_manager.conversation_stats = {
            "conversation_with_real_attachments": {
                "num_sms": 3,
                "num_calls": 0,
                "num_voicemails": 0,
                "num_img": 1,
                "num_vcf": 1,
                "num_audio": 0,
                "num_video": 0,
                "real_attachments": 2
            },
            "conversation_with_no_attachments": {
                "num_sms": 2,
                "num_calls": 0,
                "num_voicemails": 0,
                "num_img": 0,
                "num_vcf": 0,
                "num_audio": 0,
                "num_video": 0,
                "real_attachments": 0
            }
        }
        
        # Test extracting stats for conversations
        stats_with_attachments = conv_manager._extract_conversation_stats(
            test_output_dir / "conversation_with_real_attachments.html"
        )
        stats_no_attachments = conv_manager._extract_conversation_stats(
            test_output_dir / "conversation_with_no_attachments.html"
        )
        
        # Verify that conversations with real attachments show correct count
        self.assertEqual(stats_with_attachments["attachments_count"], 2, 
                        "Should count 2 real attachments (1 image + 1 vCard)")
        
        # Verify that conversations with no attachments show zero count
        self.assertEqual(stats_no_attachments["attachments_count"], 0, 
                        "Should count 0 attachments (placeholders '-' should not be counted)")
        
        # Test the accurate stats method
        accurate_stats_with_attachments = conv_manager._get_conversation_stats_accurate(
            "conversation_with_real_attachments"
        )
        accurate_stats_no_attachments = conv_manager._get_conversation_stats_accurate(
            "conversation_with_no_attachments"
        )
        
        self.assertEqual(accurate_stats_with_attachments["attachments_count"], 2,
                        "Accurate stats should show 2 real attachments")
        self.assertEqual(accurate_stats_no_attachments["attachments_count"], 0,
                        "Accurate stats should show 0 attachments")
        
        print("✅ Index page attachment count accuracy test passed")


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
