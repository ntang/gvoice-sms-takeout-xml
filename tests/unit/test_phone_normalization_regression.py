#!/usr/bin/env python3
"""
Phone Number Normalization Regression Tests
Critical tests to prevent phone number formatting bugs that corrupt the pipeline.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.pipeline.stages.phone_discovery import PhoneDiscoveryStage


class TestPhoneNormalizationRegression(unittest.TestCase):
    """Regression tests for phone number normalization bugs."""
    
    def setUp(self):
        """Set up test instance."""
        self.phone_discovery = PhoneDiscoveryStage()
    
    def test_11_digit_us_number_normalization(self):
        """
        REGRESSION TEST: Ensure 11-digit US numbers (1xxxxxxxxxx) are normalized correctly.
        
        BUG: Line 205 in phone_discovery.py was doing:
        return f"+{cleaned}"  # WRONG: +1000000000 (11 digits after +1)
        
        Should be:
        return f"+1{cleaned[1:]}"  # CORRECT: +1000000000 (10 digits after +1)
        """
        test_cases = [
            # (input, expected_output)
            ("10000000000", "+10000000000"),  # 11-digit starting with 1
            ("12025551234", "+12025551234"),  # Real US number format
            ("15551234567", "+15551234567"),  # Another US number
            ("18005551234", "+18005551234"),  # Toll-free number
        ]
        
        for input_number, expected in test_cases:
            with self.subTest(input_number=input_number):
                result = self.phone_discovery._normalize_phone_number(input_number)
                self.assertEqual(result, expected, 
                    f"Input '{input_number}' should normalize to '{expected}', got '{result}'")
                
                # Verify the result has exactly 12 characters (+1 + 10 digits)
                self.assertEqual(len(result), 12, 
                    f"Normalized US number should be 12 chars (+1 + 10 digits), got {len(result)} for '{result}'")
                
                # Verify it starts with +1
                self.assertTrue(result.startswith("+1"), 
                    f"Normalized US number should start with '+1', got '{result}'")
    
    def test_10_digit_us_number_normalization(self):
        """Test that 10-digit numbers get +1 prefix correctly."""
        test_cases = [
            ("2025551234", "+12025551234"),  # DC number
            ("5551234567", "+15551234567"),  # Generic number
            ("8005551234", "+18005551234"),  # Toll-free
        ]
        
        for input_number, expected in test_cases:
            with self.subTest(input_number=input_number):
                result = self.phone_discovery._normalize_phone_number(input_number)
                self.assertEqual(result, expected)
                self.assertEqual(len(result), 12)  # +1 + 10 digits
    
    def test_already_formatted_numbers(self):
        """Test that already correctly formatted numbers remain unchanged."""
        test_cases = [
            ("+12025551234", "+12025551234"),  # Already correct
            ("+15551234567", "+15551234567"),  # Already correct
            ("+18005551234", "+18005551234"),  # Toll-free already correct
        ]
        
        for input_number, expected in test_cases:
            with self.subTest(input_number=input_number):
                result = self.phone_discovery._normalize_phone_number(input_number)
                self.assertEqual(result, expected)
    
    def test_international_numbers(self):
        """Test that international numbers are handled correctly."""
        test_cases = [
            ("+442071234567", "+442071234567"),  # UK number
            ("+33123456789", "+33123456789"),    # French number
            ("+81312345678", "+81312345678"),    # Japanese number
        ]
        
        for input_number, expected in test_cases:
            with self.subTest(input_number=input_number):
                result = self.phone_discovery._normalize_phone_number(input_number)
                self.assertEqual(result, expected)
    
    def test_malformed_input_rejection(self):
        """Test that malformed inputs are rejected (return empty string)."""
        invalid_inputs = [
            "",              # Empty string
            "123",           # Too short
            "12345",         # Too short
            "abc",           # Non-numeric
            "+",             # Just plus sign
            "++12345678901", # Double plus
            "12345678901234567890",  # Too long
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(invalid_input=invalid_input):
                result = self.phone_discovery._normalize_phone_number(invalid_input)
                self.assertEqual(result, "", 
                    f"Invalid input '{invalid_input}' should return empty string, got '{result}'")
    
    def test_double_plus_bug_prevention(self):
        """
        REGRESSION TEST: Prevent the double plus bug (+1+xxxxxxxxx).
        
        This bug occurs when phone extraction finds malformed HTML content.
        """
        malformed_inputs = [
            "+1+2025551234",  # Double plus format
            "++12025551234",  # Double plus at start
            "+1+5551234567",  # Another double plus
        ]
        
        for malformed_input in malformed_inputs:
            with self.subTest(malformed_input=malformed_input):
                result = self.phone_discovery._normalize_phone_number(malformed_input)
                
                # Should either normalize correctly or reject
                if result:
                    # If normalized, should not contain double plus
                    self.assertNotIn("++", result, 
                        f"Normalized result should not contain '++': '{result}'")
                    self.assertFalse(result.startswith("+1+"), 
                        f"Normalized result should not start with '+1+': '{result}'")
                    
                    # Should be valid format
                    self.assertTrue(result.startswith("+"), 
                        f"Normalized result should start with '+': '{result}'")
    
    def test_format_consistency_with_conversation_files(self):
        """
        CRITICAL TEST: Ensure normalized numbers match conversation file naming.
        
        Conversation files are named like: +12025551234.html
        Normalized numbers must match this exact format for frequency analysis to work.
        """
        test_cases = [
            # (input_from_html, expected_conversation_filename_stem)
            ("10000000000", "+10000000000"),
            ("12025551234", "+12025551234"), 
            ("2025551234", "+12025551234"),
            ("+12025551234", "+12025551234"),
        ]
        
        for input_number, expected_filename_stem in test_cases:
            with self.subTest(input_number=input_number):
                normalized = self.phone_discovery._normalize_phone_number(input_number)
                self.assertEqual(normalized, expected_filename_stem,
                    f"Normalized '{input_number}' should match conversation filename stem '{expected_filename_stem}'")
    
    def test_bulk_normalization_consistency(self):
        """Test that bulk normalization produces consistent results."""
        # Test multiple formats of the same number
        same_number_formats = [
            "2025551234",      # 10 digits
            "12025551234",     # 11 digits with 1
            "+12025551234",    # Already formatted
            "+1 (202) 555-1234",  # Formatted with spaces/parens
            "202-555-1234",    # Dashed format
            "(202) 555-1234",  # Parentheses format
        ]
        
        expected = "+12025551234"
        results = []
        
        for format_variant in same_number_formats:
            result = self.phone_discovery._normalize_phone_number(format_variant)
            results.append(result)
        
        # All should normalize to the same result
        for i, result in enumerate(results):
            with self.subTest(format_variant=same_number_formats[i]):
                self.assertEqual(result, expected,
                    f"Format '{same_number_formats[i]}' should normalize to '{expected}', got '{result}'")
        
        # All results should be identical
        unique_results = set(results)
        self.assertEqual(len(unique_results), 1,
            f"All format variants should produce the same result. Got: {unique_results}")


class TestPhoneExtractionRegression(unittest.TestCase):
    """Regression tests for phone number extraction from HTML."""
    
    def setUp(self):
        """Set up test instance."""
        self.phone_discovery = PhoneDiscoveryStage()
    
    def test_html_filename_extraction_consistency(self):
        """
        Test that phone numbers extracted from HTML match the filename format.
        
        This ensures frequency analysis will work correctly.
        """
        # Test HTML content with phone numbers in formats that the patterns should match
        test_cases = [
            # (html_content, expected_to_find_number)
            ("Message from 202-555-1234", True),    # xxx-xxx-xxxx format
            ("Contact: (202) 555-1234", True),      # (xxx) xxx-xxxx format  
            ("Call 2025551234", True),               # xxxxxxxxxx format
            ("Number: +12025551234", True),          # +1xxxxxxxxxx format
        ]
        
        expected_normalized = "+12025551234"
        
        for html_content, should_find in test_cases:
            with self.subTest(html_content=html_content):
                # Extract numbers from HTML content
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text()
                
                found_numbers = set()
                for pattern in self.phone_discovery.phone_patterns:
                    import re
                    matches = re.findall(pattern, text_content)
                    for match in matches:
                        normalized = self.phone_discovery._normalize_phone_number(match)
                        if normalized:
                            found_numbers.add(normalized)
                
                if should_find:
                    # Should find the expected number
                    self.assertIn(expected_normalized, found_numbers,
                        f"Should extract '{expected_normalized}' from HTML: '{html_content}'. Found: {found_numbers}")
                else:
                    # Test case where we don't expect to find it
                    self.assertNotIn(expected_normalized, found_numbers,
                        f"Should NOT extract '{expected_normalized}' from HTML: '{html_content}'. Found: {found_numbers}")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
