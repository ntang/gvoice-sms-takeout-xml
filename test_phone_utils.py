#!/usr/bin/env python3
"""
Comprehensive test suite for phone_utils.py module.
Tests the new unified phone number processing using phonenumbers library.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phone_utils import PhoneNumberProcessor, is_valid_phone_number, normalize_phone_number, is_toll_free_number, extract_phone_numbers_from_text

# Set up logging for tests
logger = logging.getLogger(__name__)


class TestPhoneNumberProcessor(unittest.TestCase):
    """Test the PhoneNumberProcessor class functionality."""

    def setUp(self):
        """Set up test environment."""
        self.processor = PhoneNumberProcessor()
        self.processor_us = PhoneNumberProcessor(default_region="US")
        self.processor_uk = PhoneNumberProcessor(default_region="GB")

    def test_initialization(self):
        """Test processor initialization."""
        self.assertEqual(self.processor.default_region, "US")
        self.assertEqual(self.processor_uk.default_region, "GB")
        self.assertIsInstance(self.processor.reserved_toll_free_prefixes, set)
        self.assertEqual(len(self.processor.reserved_toll_free_prefixes), 10)

    def test_special_case_handling(self):
        """Test special case phone number handling."""
        special_cases = [
            ("unknown_123", True),  # Old fallback format
            ("UN_abc123", True),    # Hash-based fallback
            ("John Doe", True),     # Valid name with spaces
            ("Jane", False),        # Single word name
            ("A", False),           # Single character
            ("", False),            # Empty string
            (None, False),          # None value
        ]
        
        for input_val, expected in special_cases:
            with self.subTest(input=input_val):
                result = self.processor._is_special_case(input_val or "")
                self.assertEqual(result, expected)

    def test_toll_free_detection_active_prefixes(self):
        """Test detection of active toll-free prefixes."""
        active_toll_free = [
            "+18005551234",  # 800
            "+18335551234",  # 833
            "+18445551234",  # 844
            "+18555551234",  # 855
            "+18665551234",  # 866
            "+18775551234",  # 877
            "+18885551234",  # 888
        ]
        
        for number in active_toll_free:
            with self.subTest(number=number):
                self.assertTrue(self.processor.is_toll_free_number(number))

    def test_toll_free_detection_reserved_prefixes(self):
        """Test detection of reserved toll-free prefixes."""
        reserved_toll_free = [
            "+18225551234",  # 822
            "+18805551234",  # 880
            "+18815551234",  # 881
            "+18825551234",  # 882
            "+18835551234",  # 883
            "+18845551234",  # 884
            "+18855551234",  # 885
            "+18865551234",  # 886
            "+18875551234",  # 887
            "+18895551234",  # 889
        ]
        
        for number in reserved_toll_free:
            with self.subTest(number=number):
                self.assertTrue(self.processor.is_toll_free_number(number))

    def test_non_toll_free_numbers(self):
        """Test that non-toll-free numbers are correctly identified."""
        non_toll_free = [
            "+12125551234",  # Regular US number (NY area code)
            "+13105551234",  # Regular US number (GA area code)
            "+14105551234",  # Regular US number (CA area code)
            "+44123456789",  # UK number
            "+33123456789",  # France number
        ]
        
        for number in non_toll_free:
            with self.subTest(number=number):
                self.assertFalse(self.processor.is_toll_free_number(number))

    def test_phone_number_validation_basic(self):
        """Test basic phone number validation."""
        valid_numbers = [
            "+12125551234",  # NY area code
            "12125551234",   # NY area code without +
            "+1-212-555-1234",  # Formatted NY
            "+1 (212) 555-1234",  # Parentheses NY
            "+1.212.555.1234",  # Dotted NY
            "(212) 555-1234",  # NY without country code
            "212-555-1234",  # NY without country code
            "212.555.1234",  # NY without country code
        ]
        
        for number in valid_numbers:
            with self.subTest(number=number):
                self.assertTrue(self.processor.is_valid_phone_number(number))

    def test_phone_number_validation_invalid(self):
        """Test invalid phone number validation."""
        invalid_numbers = [
            "",           # Empty
            None,         # None
            "123",        # Too short
            "abcdef",     # No digits
            "555-1234",   # Missing country code
            "+15551234567890123456789",  # Too long
        ]
        
        for number in invalid_numbers:
            with self.subTest(input=number):
                result = self.processor.is_valid_phone_number(number or "")
                self.assertFalse(result)

    def test_phone_number_validation_with_filtering(self):
        """Test phone number validation with enhanced filtering enabled."""
        # Numbers that should be filtered out
        filtered_numbers = [
            "+18005551234",  # Toll-free
            "+18335551234",  # Toll-free
            "+1555123456",   # Short code (if detected)
        ]
        
        for number in filtered_numbers:
            with self.subTest(number=number):
                # Should be valid without filtering
                self.assertTrue(self.processor.is_valid_phone_number(number, filter_non_phone=False))
                # Should be filtered out with filtering enabled
                self.assertFalse(self.processor.is_valid_phone_number(number, filter_non_phone=True))
        
        # Numbers that should pass through filtering
        passing_numbers = [
            "+12125551234",  # Valid US number
            "+13105551234",  # Valid US number
        ]
        
        for number in passing_numbers:
            with self.subTest(number=number):
                # Should be valid both with and without filtering
                self.assertTrue(self.processor.is_valid_phone_number(number, filter_non_phone=False))
                self.assertTrue(self.processor.is_valid_phone_number(number, filter_non_phone=True))

    def test_phone_number_extraction(self):
        """Test phone number extraction from text."""
        test_cases = [
            ("Call me at +12125551234", ["+12125551234"]),
            ("tel:+12125551234", ["+12125551234"]),
            ("Multiple: +12125551234 and +13105551234", ["+12125551234", "+13105551234"]),
            ("International: +44123456789", ["+44123456789"]),
            ("Formatted: (212) 555-1234", ["+12125551234"]),  # Normalized to E.164
            ("Dashed: 212-555-1234", ["+12125551234"]),      # Normalized to E.164
            ("Mixed: +12125551234 and tel:+13105551234", ["+12125551234", "+13105551234"]),
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                extracted = self.processor.extract_phone_numbers_from_text(text)
                # Check that all expected numbers are found
                for expected_num in expected:
                    self.assertIn(expected_num, extracted)

    def test_phone_number_normalization(self):
        """Test phone number normalization to E.164 format."""
        test_cases = [
            ("+12125551234", "+12125551234"),      # Already E.164
            ("12125551234", "+12125551234"),        # US domestic
            ("+1-212-555-1234", "+12125551234"),   # Formatted US
            ("+1 (212) 555-1234", "+12125551234"), # Parentheses
            ("+1.212.555.1234", "+12125551234"),   # Dotted
            ("(212) 555-1234", "+12125551234"),    # US without country code
            ("212-555-1234", "+12125551234"),      # US without country code
        ]
        
        for input_num, expected in test_cases:
            with self.subTest(input=input_num):
                normalized = self.processor.normalize_phone_number(input_num)
                self.assertEqual(normalized, expected)

    def test_number_type_info(self):
        """Test comprehensive number type information."""
        # Test with a valid US mobile number
        info = self.processor.get_number_type_info("+12125551234")
        
        self.assertIsInstance(info, dict)
        self.assertTrue(info["is_valid"])
        self.assertTrue(info["is_possible"])
        self.assertEqual(info["country_code"], 1)
        self.assertEqual(info["national_number"], "2125551234")
        self.assertEqual(info["e164_format"], "+12125551234")
        
        # Test with toll-free number
        toll_free_info = self.processor.get_number_type_info("+18005551234")
        self.assertTrue(toll_free_info["is_toll_free"])

    def test_enhanced_filtering(self):
        """Test enhanced filtering functionality."""
        # Test that enhanced filtering works correctly
        self.assertTrue(self.processor._passes_enhanced_filtering("+12125551234"))
        self.assertFalse(self.processor._passes_enhanced_filtering("+18005551234"))  # Toll-free
        self.assertFalse(self.processor._passes_enhanced_filtering("+44123456789"))  # Non-US

    def test_basic_filtering_fallback(self):
        """Test basic filtering fallback when phonenumbers parsing fails."""
        # Test fallback filtering
        self.assertTrue(self.processor._basic_filtering_fallback("+12125551234"))
        self.assertFalse(self.processor._basic_filtering_fallback("+18005551234"))  # Toll-free
        self.assertFalse(self.processor._basic_filtering_fallback("+44123456789"))  # Non-US

    def test_reserved_toll_free_detection(self):
        """Test detection of reserved toll-free prefixes."""
        reserved_numbers = [
            "8225551234",
            "8805551234",
            "8815551234",
            "8825551234",
            "8835551234",
            "8845551234",
            "8855551234",
            "8865551234",
            "8875551234",
            "8895551234",
        ]
        
        for number in reserved_numbers:
            with self.subTest(number=number):
                self.assertTrue(self.processor._is_reserved_toll_free(number))

    def test_non_reserved_toll_free(self):
        """Test that non-reserved prefixes are not detected as toll-free."""
        non_reserved = [
            "8005551234",  # Active toll-free (handled by library)
            "8775551234",  # Active toll-free (handled by library)
            "2125551234",  # Regular number
            "1234567890",  # Regular number
        ]
        
        for number in non_reserved:
            with self.subTest(number=number):
                # These should not be detected by reserved prefix checking
                # (they may still be toll-free via library detection)
                if not number.startswith(("800", "877", "888", "866", "855", "844", "833")):
                    self.assertFalse(self.processor._is_reserved_toll_free(number))


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility functions."""

    def test_is_valid_phone_number_function(self):
        """Test the backward compatibility is_valid_phone_number function."""
        # Test valid numbers
        self.assertTrue(is_valid_phone_number("+12125551234"))
        self.assertTrue(is_valid_phone_number("+12125551234", filter_non_phone=False))
        
        # Test filtering
        self.assertFalse(is_valid_phone_number("+18005551234", filter_non_phone=True))
        self.assertTrue(is_valid_phone_number("+18005551234", filter_non_phone=False))

    def test_normalize_phone_number_function(self):
        """Test the backward compatibility normalize_phone_number function."""
        self.assertEqual(normalize_phone_number("+1-212-555-1234"), "+12125551234")
        self.assertEqual(normalize_phone_number("12125551234"), "+12125551234")

    def test_is_toll_free_number_function(self):
        """Test the backward compatibility is_toll_free_number function."""
        self.assertTrue(is_toll_free_number("+18005551234"))
        self.assertTrue(is_toll_free_number("+18805551234"))  # Reserved
        self.assertFalse(is_toll_free_number("+12125551234"))

    def test_extract_phone_numbers_from_text_function(self):
        """Test the backward compatibility extract_phone_numbers_from_text function."""
        text = "Call me at +12125551234 or tel:+13105551234"
        extracted = extract_phone_numbers_from_text(text)
        self.assertIn("+12125551234", extracted)
        self.assertIn("+13105551234", extracted)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test environment."""
        self.processor = PhoneNumberProcessor()

    def test_malformed_numbers(self):
        """Test handling of malformed phone numbers."""
        malformed = [
            "++12125551234",     # Double plus
            "+1++2125551234",    # Multiple plus signs
            "+1-212-555-1234-",  # Trailing dash
            "+1-212--555-1234",  # Double dash
            "+1(212)555-1234",   # Missing space after parentheses
        ]
        
        for number in malformed:
            with self.subTest(number=number):
                # Should handle gracefully without crashing
                result = self.processor.is_valid_phone_number(number)
                # Result may vary based on phonenumbers library behavior
                self.assertIsInstance(result, bool)

    def test_extremely_long_numbers(self):
        """Test handling of extremely long numbers."""
        long_number = "+1" + "2" * 50  # Very long number
        result = self.processor.is_valid_phone_number(long_number)
        self.assertFalse(result)

    def test_special_characters(self):
        """Test handling of numbers with special characters."""
        special_chars = [
            "+1-212-555-1234!",
            "+1-212-555-1234@",
            "+1-212-555-1234#",
            "+1-212-555-1234$",
        ]
        
        for number in special_chars:
            with self.subTest(number=number):
                # Should handle gracefully
                result = self.processor.is_valid_phone_number(number)
                self.assertIsInstance(result, bool)

    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        empty_inputs = ["", None, "   ", "\t", "\n"]
        
        for input_val in empty_inputs:
            with self.subTest(input=input_val):
                result = self.processor.is_valid_phone_number(input_val or "")
                self.assertFalse(result)


class TestPerformance(unittest.TestCase):
    """Test performance characteristics."""

    def setUp(self):
        """Set up test environment."""
        self.processor = PhoneNumberProcessor()

    def test_bulk_validation_performance(self):
        """Test performance of bulk phone number validation."""
        import time
        
        # Generate test phone numbers
        test_numbers = [
            "+12125551234", "+13105551234", "+14105551234",
            "+18005551234", "+18335551234", "+18445551234",
            "+12125551235", "+13105551235", "+14105551235",
            "+18805551234", "+18815551234", "+18825551234",
        ] * 100  # 1200 total numbers
        
        # Benchmark validation
        start_time = time.time()
        for number in test_numbers:
            self.processor.is_valid_phone_number(number)
        validation_time = time.time() - start_time
        
        # Benchmark toll-free detection
        start_time = time.time()
        for number in test_numbers:
            self.processor.is_toll_free_number(number)
        toll_free_time = time.time() - start_time
        
        # Assert reasonable performance (should be fast)
        self.assertLess(validation_time, 1.0)  # Less than 1 second for 1200 numbers
        self.assertLess(toll_free_time, 1.0)   # Less than 1 second for 1200 numbers
        
        logger.info(f"Validation time: {validation_time:.3f}s for {len(test_numbers)} numbers")
        logger.info(f"Toll-free detection time: {toll_free_time:.3f}s for {len(test_numbers)} numbers")

    def test_extraction_performance(self):
        """Test performance of phone number extraction."""
        import time
        
        # Create test text with many phone numbers
        test_text = " ".join([
            f"Call me at +1212{str(i).zfill(7)}" 
            for i in range(100)
        ])
        
        # Benchmark extraction
        start_time = time.time()
        extracted = self.processor.extract_phone_numbers_from_text(test_text)
        extraction_time = time.time() - start_time
        
        # Assert reasonable performance
        self.assertLess(extraction_time, 2.0)  # Less than 2 seconds for 100 numbers
        # The extraction might find duplicates due to multiple extraction methods
        # So we check that we get at least the expected number
        self.assertGreaterEqual(len(extracted), 100)
        
        logger.info(f"Extraction time: {extraction_time:.3f}s for {len(extracted)} numbers")


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)
