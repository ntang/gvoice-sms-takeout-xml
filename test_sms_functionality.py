#!/usr/bin/env python3
"""
Comprehensive test suite for SMS functionality to prevent regressions.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import is_valid_phone_number
from phone_lookup import PhoneLookupManager


class TestPhoneNumberValidation(unittest.TestCase):
    """Test phone number validation functionality."""

    def test_valid_us_phone_numbers(self):
        """Test that valid US phone numbers are accepted."""
        valid_numbers = [
            "+15551234567",
            "+15551234567",
            "15551234567",
            "+1-555-123-4567",
            "+1 (555) 123-4567",
            "+1.555.123.4567",
        ]

        for number in valid_numbers:
            with self.subTest(number=number):
                self.assertTrue(is_valid_phone_number(number))

    def test_invalid_phone_numbers(self):
        """Test that invalid phone numbers are rejected."""
        invalid_numbers = [
            "123",  # Too short
            "123456",  # Too short
            "abcdef",  # No digits
            "",  # Empty
            None,  # None
            "555-1234",  # Missing country code
        ]

        for number in invalid_numbers:
            with self.subTest(number=number):
                self.assertFalse(is_valid_phone_number(number))

    def test_toll_free_filtering(self):
        """Test toll-free number filtering."""
        toll_free_numbers = [
            "+18005551234",  # 800
            "+18775551234",  # 877
            "+18885551234",  # 888
            "+18665551234",  # 866
            "+18555551234",  # 855
        ]

        for number in toll_free_numbers:
            with self.subTest(number=number):
                # Should be valid without filtering
                self.assertTrue(is_valid_phone_number(number, filter_non_phone=False))
                # Should be filtered out with filtering enabled
                self.assertFalse(is_valid_phone_number(number, filter_non_phone=True))

    def test_non_us_filtering(self):
        """Test non-US number filtering."""
        non_us_numbers = [
            "+44123456789",  # UK
            "+33123456789",  # France
            "+49123456789",  # Germany
            "+81123456789",  # Japan
        ]

        for number in non_us_numbers:
            with self.subTest(number=number):
                # Should be valid without filtering
                self.assertTrue(is_valid_phone_number(number, filter_non_phone=False))
                # Should be filtered out with filtering enabled
                self.assertFalse(is_valid_phone_number(number, filter_non_phone=True))

    def test_name_handling(self):
        """Test that names are handled correctly."""
        names = ["John Doe", "Jane Smith", "Bob Wilson", "Alice Johnson"]

        for name in names:
            with self.subTest(name=name):
                # Names should always be valid
                self.assertTrue(is_valid_phone_number(name, filter_non_phone=False))
                self.assertTrue(is_valid_phone_number(name, filter_non_phone=True))


class TestPhoneLookupManager(unittest.TestCase):
    """Test PhoneLookupManager functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.lookup_file = Path(self.temp_dir) / "phone_lookup.txt"
        self.phone_manager = PhoneLookupManager(self.lookup_file, enable_prompts=False)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_add_and_get_alias(self):
        """Test adding and retrieving aliases."""
        phone = "+15551234567"
        alias = "Test User"

        # Add alias
        self.phone_manager.add_alias(phone, alias)

        # Retrieve alias (should be sanitized)
        retrieved = self.phone_manager.get_alias(phone)
        self.assertEqual(retrieved, "Test_User")  # Sanitized version

    def test_alias_persistence(self):
        """Test that aliases are persisted to disk."""
        phone = "+15551234567"
        alias = "Test User"

        # Add alias
        self.phone_manager.add_alias(phone, alias)

        # Create new manager instance to test persistence
        new_manager = PhoneLookupManager(self.lookup_file, enable_prompts=False)

        # Retrieve alias (should be sanitized)
        retrieved = new_manager.get_alias(phone)
        self.assertEqual(retrieved, "Test_User")  # Sanitized version

    def test_exclusion_functionality(self):
        """Test phone number exclusion functionality."""
        phone = "+15551234567"
        reason = "Test exclusion"

        # Add exclusion
        self.phone_manager.add_exclusion(phone, reason)

        # Check exclusion
        self.assertTrue(self.phone_manager.is_excluded(phone))
        self.assertEqual(self.phone_manager.get_exclusion_reason(phone), reason)

    def test_has_alias_functionality(self):
        """Test has_alias functionality."""
        phone = "+15551234567"
        alias = "Test User"

        # Initially no alias
        self.assertFalse(self.phone_manager.has_alias(phone))

        # Add alias
        self.phone_manager.add_alias(phone, alias)

        # Now has alias
        self.assertTrue(self.phone_manager.has_alias(phone))

    def test_sanitize_alias(self):
        """Test alias sanitization."""
        test_cases = [
            ("John Doe", "John_Doe"),
            ("Bob Wilson!", "Bob_Wilson"),
            ("Alice@Johnson", "AliceJohnson"),  # @ is removed, no underscore added
            ("Test User-Name", "Test_User_Name"),
            ("", "unknown"),
            ("   ", "unknown"),
        ]

        for input_alias, expected in test_cases:
            with self.subTest(input_alias=input_alias):
                result = self.phone_manager.sanitize_alias(input_alias)
                self.assertEqual(result, expected)


class TestSMSProcessing(unittest.TestCase):
    """Test SMS processing functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.temp_dir) / "test_data"
        self.test_data_dir.mkdir()

        # Create test HTML files
        self.create_test_html_files()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def create_test_html_files(self):
        """Create test HTML files for testing."""
        # Create a simple test HTML file
        test_html = """
        <html>
        <body>
            <div class="message">
                <abbr class="dt" title="2024-01-01T12:00:00Z">Jan 01</abbr>
                <cite><a href="tel:+15551234567">Test User</a></cite>
                <q>Hello, this is a test message!</q>
            </div>
            <div class="message">
                <abbr class="dt" title="2024-01-01T12:01:00Z">Jan 01</abbr>
                <cite>Me</cite>
                <q>This is a response message.</q>
            </div>
        </body>
        </html>
        """

        test_file = self.test_data_dir / "Test User - Text - 2024-01-01T12_00_00Z.html"
        test_file.write_text(test_html)

    def test_html_file_creation(self):
        """Test that test HTML files are created correctly."""
        test_file = self.test_data_dir / "Test User - Text - 2024-01-01T12_00_00Z.html"
        self.assertTrue(test_file.exists())
        self.assertGreater(test_file.stat().st_size, 0)

    def test_phone_number_extraction(self):
        """Test phone number extraction from HTML."""
        from utils import extract_phone_numbers_from_text

        test_html = """
        <a href="tel:+15551234567">Test User</a>
        <a href="tel:+15559876543">Another User</a>
        """

        phone_numbers = extract_phone_numbers_from_text(test_html)
        self.assertIn("+15551234567", phone_numbers)
        self.assertIn("+15559876543", phone_numbers)
        # The function finds both tel: links and plain numbers, so we expect 4 total
        self.assertEqual(len(phone_numbers), 4)


class TestConfiguration(unittest.TestCase):
    """Test configuration functionality."""

    def test_config_imports(self):
        """Test that all configuration modules can be imported."""
        try:
            from config import DEFAULT_CONFIG
            from conversation_manager import ConversationManager
            from phone_lookup import PhoneLookupManager
            from utils import is_valid_phone_number

            self.assertTrue(True)  # If we get here, imports worked
        except ImportError as e:
            self.fail(f"Failed to import required modules: {e}")

    def test_config_constants(self):
        """Test that configuration constants are properly defined."""
        from config import DEFAULT_CONFIG

        required_keys = [
            "SUPPORTED_IMAGE_TYPES",
            "SUPPORTED_VCARD_TYPES",
            "MMS_TYPE_SENT",
            "MMS_TYPE_RECEIVED",
            "MESSAGE_BOX_SENT",
            "MESSAGE_BOX_RECEIVED",
        ]

        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, DEFAULT_CONFIG)


def run_tests():
    """Run all tests."""
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestPhoneNumberValidation,
        TestPhoneLookupManager,
        TestSMSProcessing,
        TestConfiguration,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
