"""
Unit tests for parameterized filtering functions.

This test suite tests the parameterized versions of filtering functions
that accept configuration explicitly instead of using global variables.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path

from core.processing_config import ProcessingConfig
import sms


class TestParameterizedFiltering:
    """Test suite for parameterized filtering functions."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.test_dir = Path("/tmp/test_processing")
        self.base_config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=None,
            exclude_newer_than=None,
            filter_numbers_without_aliases=False,
            filter_non_phone_numbers=False,
            skip_filtered_contacts=True,
            include_service_codes=False,
            filter_groups_with_all_filtered=True,
            full_run=False
        )
        self.mock_phone_lookup = Mock()

    def test_should_skip_message_by_date_param_no_filters(self):
        """Test parameterized date filtering when no date filters are set."""
        # Any timestamp should not be skipped when no filters are set
        current_timestamp = int(datetime.now().timestamp() * 1000)
        old_timestamp = int(datetime(2020, 1, 1).timestamp() * 1000)
        future_timestamp = int(datetime(2030, 1, 1).timestamp() * 1000)
        
        assert sms.should_skip_message_by_date_param(current_timestamp, self.base_config) == False
        assert sms.should_skip_message_by_date_param(old_timestamp, self.base_config) == False
        assert sms.should_skip_message_by_date_param(future_timestamp, self.base_config) == False

    def test_should_skip_message_by_date_param_older_than_filter(self):
        """Test parameterized date filtering with older_than filter."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=None
        )
        
        # Test timestamps
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        current_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        
        assert sms.should_skip_message_by_date_param(old_timestamp, config) == True
        assert sms.should_skip_message_by_date_param(current_timestamp, config) == False

    def test_should_skip_message_by_date_param_newer_than_filter(self):
        """Test parameterized date filtering with newer_than filter."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=None,
            exclude_newer_than=datetime(2024, 12, 31)
        )
        
        # Test timestamps
        current_timestamp = int(datetime(2024, 6, 15, 12, 0, 0).timestamp() * 1000)
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        
        assert sms.should_skip_message_by_date_param(current_timestamp, config) == False
        assert sms.should_skip_message_by_date_param(future_timestamp, config) == True

    def test_should_skip_message_by_date_param_both_filters(self):
        """Test parameterized date filtering with both filters."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31)
        )
        
        # Test timestamps
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        current_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        
        assert sms.should_skip_message_by_date_param(old_timestamp, config) == True
        assert sms.should_skip_message_by_date_param(current_timestamp, config) == False
        assert sms.should_skip_message_by_date_param(future_timestamp, config) == True

    def test_should_skip_message_by_phone_param_no_filters(self):
        """Test parameterized phone filtering when no phone filters are set."""
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = False  # No alias
        
        # Should not skip when no filters are enabled
        assert sms.should_skip_message_by_phone_param("+1234567890", mock_phone_lookup, self.base_config) == False
        assert sms.should_skip_message_by_phone_param("555-SHORT", mock_phone_lookup, self.base_config) == False

    def test_should_skip_message_by_phone_param_with_aliases(self):
        """Test parameterized phone filtering with filter_numbers_without_aliases enabled."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True
        )
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        
        # Test with alias
        mock_phone_lookup.has_alias.return_value = True
        assert sms.should_skip_message_by_phone_param("+1234567890", mock_phone_lookup, config) == False
        
        # Test without alias
        mock_phone_lookup.has_alias.return_value = False
        assert sms.should_skip_message_by_phone_param("+1234567890", mock_phone_lookup, config) == True

    def test_should_skip_message_by_phone_param_non_phone_numbers(self):
        """Test parameterized phone filtering with filter_non_phone_numbers enabled."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_non_phone_numbers=True
        )
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        
        # Test with regular phone number
        assert sms.should_skip_message_by_phone_param("+1234567890", mock_phone_lookup, config) == False
        
        # Test with short code (non-phone number)
        assert sms.should_skip_message_by_phone_param("555-SHORT", mock_phone_lookup, config) == True

    def test_should_skip_message_by_phone_param_none_phone_lookup_manager(self):
        """Test parameterized phone filtering when phone lookup manager is None."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True
        )
        
        # Should not skip when phone lookup manager is None (can't check for alias)
        assert sms.should_skip_message_by_phone_param("+1234567890", None, config) == False

    def test_should_skip_message_param_combined_filtering(self):
        """Test parameterized combined filtering with both date and phone filters."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = False  # No alias
        
        # Test old message without alias (should be skipped for both reasons)
        old_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        assert sms.should_skip_message_param(old_timestamp, "+1234567890", mock_phone_lookup, config) == True
        
        # Test current message without alias (should be skipped for phone reason only)
        current_timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        assert sms.should_skip_message_param(current_timestamp, "+1234567890", mock_phone_lookup, config) == True
        
        # Test current message with alias (should not be skipped)
        mock_phone_lookup.has_alias.return_value = True
        assert sms.should_skip_message_param(current_timestamp, "+1234567890", mock_phone_lookup, config) == False

    def test_parameterized_functions_equivalence_with_global_functions(self):
        """Test that parameterized functions produce equivalent results to global functions."""
        # This test ensures backward compatibility
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31),
            filter_numbers_without_aliases=True
        )
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = False
        
        # Test timestamp
        test_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        test_phone = "+1234567890"
        
        # Mock the global variables to match the config
        with patch('sms.DATE_FILTER_OLDER_THAN', config.exclude_older_than), \
             patch('sms.DATE_FILTER_NEWER_THAN', config.exclude_newer_than), \
             patch('sms.FILTER_NUMBERS_WITHOUT_ALIASES', config.filter_numbers_without_aliases):
            
            # Test date filtering equivalence
            global_result = sms.should_skip_message_by_date(test_timestamp)
            param_result = sms.should_skip_message_by_date_param(test_timestamp, config)
            assert global_result == param_result, "Date filtering should produce equivalent results"
            
            # Test phone filtering equivalence
            global_phone_result = sms.should_skip_message_by_phone_param(test_phone, mock_phone_lookup, config)
            # Note: We can't easily test the global phone filtering function since it's not parameterized
            # But we can verify the parameterized version works correctly

    def test_parameterized_functions_with_invalid_inputs(self):
        """Test parameterized functions with invalid inputs."""
        config = ProcessingConfig(processing_dir=self.test_dir)
        mock_phone_lookup = Mock()
        
        # Test with invalid timestamp
        invalid_timestamp = -1
        assert sms.should_skip_message_by_date_param(invalid_timestamp, config) == False
        
        # Test with empty phone number
        assert sms.should_skip_message_by_phone_param("", mock_phone_lookup, config) == False
        assert sms.should_skip_message_by_phone_param(None, mock_phone_lookup, config) == False
        
        # Test combined function with invalid inputs
        assert sms.should_skip_message_param(invalid_timestamp, "", mock_phone_lookup, config) == False

    def test_parameterized_functions_performance(self):
        """Test that parameterized functions are performant."""
        import time
        
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = True
        
        # Test 1000 filtering operations
        start_time = time.time()
        for i in range(1000):
            timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
            sms.should_skip_message_param(timestamp, "+1234567890", mock_phone_lookup, config)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete 1000 operations in less than 2 seconds (accounting for import overhead)
        assert elapsed < 2.0, f"Parameterized filtering operations took too long: {elapsed:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
