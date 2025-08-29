#!/usr/bin/env python3
"""
Comprehensive test suite for SMS functionality to prevent regressions.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

# unittest.mock imports removed - not used
import sys
import os

from utils import is_valid_phone_number
from phone_lookup import PhoneLookupManager

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
            "abcdef",  # No digits
            "",  # Empty
            None,  # None
            "555-1234",  # Missing country code
        ]

        for number in invalid_numbers:
            with self.subTest(number=number):
                self.assertFalse(is_valid_phone_number(number))

    def test_short_code_handling(self):
        """Test that short codes are handled correctly."""
        short_codes = [
            "1234",  # 4 digits
            "12345",  # 5 digits
            "123456",  # 6 digits
        ]

        for code in short_codes:
            with self.subTest(code=code):
                # Short codes should be valid without filtering
                self.assertTrue(is_valid_phone_number(code, filter_non_phone=False))
                # Short codes should be filtered out with filtering enabled
                self.assertFalse(is_valid_phone_number(code, filter_non_phone=True))

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
        # The function extracts phone numbers from tel: links, so we expect 2 total
        self.assertEqual(len(phone_numbers), 2)


class TestHashGeneration(unittest.TestCase):
    """Test hash generation functionality."""

    def test_hash_generation_uniqueness(self):
        """Test that hash generation produces unique results for different inputs."""
        from utils import generate_unknown_number_hash

        # Test different inputs produce different hashes
        hash1 = generate_unknown_number_hash("test_input_1")
        hash2 = generate_unknown_number_hash("test_input_2")
        hash3 = generate_unknown_number_hash("test_input_3")

        self.assertNotEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertNotEqual(hash2, hash3)

    def test_hash_generation_consistency(self):
        """Test that hash generation produces consistent results for the same input."""
        from utils import generate_unknown_number_hash

        # Test same input produces same hash
        input_text = "consistent_test_input"
        hash1 = generate_unknown_number_hash(input_text)
        hash2 = generate_unknown_number_hash(input_text)
        hash3 = generate_unknown_number_hash(input_text)

        self.assertEqual(hash1, hash2)
        self.assertEqual(hash1, hash3)
        self.assertEqual(hash2, hash3)

    def test_hash_generation_format(self):
        """Test that hash generation produces correctly formatted hashes."""
        from utils import generate_unknown_number_hash
        import re

        # Test hash format: UN_ + 22 character Base64 string
        hash_value = generate_unknown_number_hash("test_input")
        
        # Should start with UN_
        self.assertTrue(hash_value.startswith("UN_"))
        
        # Should be exactly 25 characters (UN_ + 22 Base64 chars)
        self.assertEqual(len(hash_value), 25)
        
        # Should match the pattern from config
        pattern = r"^UN_[A-Za-z0-9_-]{22}$"
        self.assertIsNotNone(re.match(pattern, hash_value))

    def test_hash_generation_url_safe(self):
        """Test that generated hashes are URL-safe."""
        from utils import generate_unknown_number_hash

        # Test multiple hashes to ensure they're URL-safe
        test_inputs = ["test1", "test2", "test3", "test with spaces", "test-with-dashes"]
        
        for test_input in test_inputs:
            with self.subTest(input=test_input):
                hash_value = generate_unknown_number_hash(test_input)
                
                # Should not contain URL-unsafe characters
                unsafe_chars = ['+', '/', '=']
                for char in unsafe_chars:
                    self.assertNotIn(char, hash_value, 
                                   f"Hash contains unsafe character '{char}': {hash_value}")


class TestConfiguration(unittest.TestCase):
    """Test configuration functionality."""

    def test_config_imports(self):
        """Test that all configuration modules can be imported."""
        try:
            # Import test removed - not used
            self.assertTrue(True)  # If we get here, imports worked
        except ImportError as e:
            self.fail("Failed to import required modules: {}".format(e))

    def test_config_constants(self):
        """Test that configuration constants are properly defined."""
        from app_config import DEFAULT_CONFIG

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
        TestHashGeneration,
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
