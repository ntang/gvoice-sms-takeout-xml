"""
Unit tests for integer phone number handling in filtering functions.

Tests verify that filtering functions handle integer phone numbers
from fallback extraction without crashing.

Bug #26: Prevents 'object of type int has no len()' TypeError
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.filtering_service import FilteringService
from core.processing_config import ProcessingConfig
from sms import should_skip_message_by_phone_param


class TestIntegerPhoneNumberFiltering:
    """Test filtering functions with integer phone number inputs."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock config with filtering enabled
        self.config = Mock(spec=ProcessingConfig)
        self.config.filter_non_phone_numbers = True
        self.config.filter_numbers_without_aliases = False
        self.config.include_service_codes = False

        # Create filtering service
        self.filtering_service = FilteringService(self.config)

        # Create mock phone lookup manager
        self.phone_lookup_manager = MagicMock()
        self.phone_lookup_manager.has_alias.return_value = True
        self.phone_lookup_manager.is_excluded.return_value = False

    def test_is_service_code_with_integer_short_code(self):
        """Test _is_service_code() with integer short code (should not crash)."""
        # Input: 22395 (int) - a 5-digit service code
        # Expected: Returns True (len("22395") = 5 <= 6), no crash
        result = self.filtering_service._is_service_code(22395)
        assert result is True, "Should detect 5-digit number as service code"

    def test_is_service_code_with_integer_full_number(self):
        """Test _is_service_code() with integer full phone number (should not crash)."""
        # Input: 17326389287 (int) - an 11-digit phone number
        # Expected: Returns False (len("17326389287") = 11 > 6), no crash
        result = self.filtering_service._is_service_code(17326389287)
        assert result is False, "Should not detect 11-digit number as service code"

    def test_is_service_code_with_zero(self):
        """Test _is_service_code() with zero (edge case, should not crash)."""
        # Input: 0 (int) - edge case when no phone number found
        # Expected: Returns True (len("0") = 1 <= 6), no crash
        result = self.filtering_service._is_service_code(0)
        assert result is True, "Should handle zero without crashing"

    def test_is_non_phone_number_with_integer(self):
        """Test _is_non_phone_number() with integer (should not crash)."""
        # Input: 8003092350 (int) - toll-free number
        # Expected: Processes correctly, no crash
        result = self.filtering_service._is_non_phone_number(8003092350)
        # Toll-free numbers start with 800, should be detected
        assert isinstance(result, bool), "Should return boolean without crashing"

    def test_should_skip_by_phone_with_integer_fallback(self):
        """Test should_skip_by_phone() with integer fallback number (should not crash)."""
        # Input: 17326389287 (int) - fallback from filename
        # Expected: Evaluates correctly, no crash
        result = self.filtering_service.should_skip_by_phone(17326389287, self.phone_lookup_manager)
        assert isinstance(result, bool), "Should return boolean without crashing"

    def test_should_skip_message_by_phone_param_with_int(self):
        """Test should_skip_message_by_phone_param() with int phone number (should not crash)."""
        # Full integration test with mock managers
        # Input: 17326389287 (int)
        # Expected: No crash
        result = should_skip_message_by_phone_param(17326389287, self.phone_lookup_manager, self.config)
        assert isinstance(result, bool), "Should return boolean without crashing"

    def test_filtering_with_negative_number(self):
        """Test filtering with negative number (edge case, should handle gracefully)."""
        # Input: -1 (shouldn't happen in practice, but defensive)
        # Expected: Handles gracefully, no crash
        result = self.filtering_service._is_service_code(-1)
        assert isinstance(result, bool), "Should handle negative numbers without crashing"

    def test_filtering_with_very_large_int(self):
        """Test filtering with very large integer (edge case, should handle gracefully)."""
        # Input: 19999999999999 (15 digits)
        # Expected: Handles gracefully, no crash
        result = self.filtering_service._is_service_code(19999999999999)
        assert result is False, "Should detect large number as not a service code"


class TestZeroPhoneNumberHandling:
    """Test special handling of phone_number=0."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock(spec=ProcessingConfig)
        self.config.filter_non_phone_numbers = False
        self.config.filter_numbers_without_aliases = False
        self.config.include_service_codes = True

        self.filtering_service = FilteringService(self.config)
        self.phone_lookup_manager = MagicMock()

    def test_should_skip_by_phone_with_zero(self):
        """Test that phone_number=0 is handled correctly (not treated as False)."""
        # Phone number 0 indicates no participant found
        # Should not be treated same as None/empty string
        result = self.filtering_service.should_skip_by_phone(0, self.phone_lookup_manager)
        # With our zero-aware check: if not phone_number and phone_number != 0
        # 0 should pass through to be converted to "0"
        assert isinstance(result, bool), "Should handle zero distinctly from None"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
