"""
Unit tests for FilteringService class.

This test suite follows TDD principles and tests the new dependency-injection
based filtering system that eliminates global variable dependencies.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from pathlib import Path

from core.filtering_service import FilteringService
from core.processing_config import ProcessingConfig


class TestFilteringService:
    """Test suite for FilteringService class."""

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

    def test_filtering_service_initialization(self):
        """Test that FilteringService initializes correctly with config."""
        service = FilteringService(self.base_config)
        
        assert service.config == self.base_config
        assert service.config.processing_dir == self.test_dir

    def test_date_filtering_no_filters(self):
        """Test date filtering when no date filters are set."""
        service = FilteringService(self.base_config)
        
        # Any timestamp should not be skipped when no filters are set
        current_timestamp = int(datetime.now().timestamp() * 1000)
        old_timestamp = int(datetime(2020, 1, 1).timestamp() * 1000)
        future_timestamp = int(datetime(2030, 1, 1).timestamp() * 1000)
        
        assert service.should_skip_by_date(current_timestamp) == False
        assert service.should_skip_by_date(old_timestamp) == False
        assert service.should_skip_by_date(future_timestamp) == False

    def test_date_filtering_older_than_only(self):
        """Test date filtering with only older_than filter set."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=None
        )
        service = FilteringService(config)
        
        # Test timestamps
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        current_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        future_timestamp = int(datetime(2024, 6, 15, 12, 0, 0).timestamp() * 1000)
        
        assert service.should_skip_by_date(old_timestamp) == True, "Old message should be skipped"
        assert service.should_skip_by_date(current_timestamp) == False, "Current message should not be skipped"
        assert service.should_skip_by_date(future_timestamp) == False, "Future message should not be skipped"

    def test_date_filtering_newer_than_only(self):
        """Test date filtering with only newer_than filter set."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=None,
            exclude_newer_than=datetime(2024, 12, 31)
        )
        service = FilteringService(config)
        
        # Test timestamps
        old_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        current_timestamp = int(datetime(2024, 6, 15, 12, 0, 0).timestamp() * 1000)
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        
        assert service.should_skip_by_date(old_timestamp) == False, "Old message should not be skipped"
        assert service.should_skip_by_date(current_timestamp) == False, "Current message should not be skipped"
        assert service.should_skip_by_date(future_timestamp) == True, "Future message should be skipped"

    def test_date_filtering_both_filters(self):
        """Test date filtering with both older_than and newer_than filters set."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31)
        )
        service = FilteringService(config)
        
        # Test timestamps
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        current_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        
        assert service.should_skip_by_date(old_timestamp) == True, "Old message should be skipped"
        assert service.should_skip_by_date(current_timestamp) == False, "Current message should not be skipped"
        assert service.should_skip_by_date(future_timestamp) == True, "Future message should be skipped"

    def test_date_filtering_edge_cases(self):
        """Test date filtering edge cases."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31)
        )
        service = FilteringService(config)
        
        # Test exact boundary timestamps
        older_boundary = int(datetime(2023, 1, 1).timestamp() * 1000)
        newer_boundary = int(datetime(2024, 12, 31, 23, 59, 59).timestamp() * 1000)
        
        # Boundary conditions - older boundary should not be skipped (inclusive)
        # newer boundary should be skipped because it's after the newer_than date
        assert service.should_skip_by_date(older_boundary) == False, "Older boundary should not be skipped"
        assert service.should_skip_by_date(newer_boundary) == True, "Newer boundary should be skipped (after newer_than)"
        
        # Test timestamps exactly at the boundary
        exactly_newer_than = int(datetime(2024, 12, 31).timestamp() * 1000)
        assert service.should_skip_by_date(exactly_newer_than) == False, "Exactly at newer_than should not be skipped"

    def test_phone_filtering_no_filters(self):
        """Test phone filtering when no phone filters are set."""
        service = FilteringService(self.base_config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = False  # No alias
        
        # Should not skip when no filters are enabled
        assert service.should_skip_by_phone("+1234567890", mock_phone_lookup) == False
        assert service.should_skip_by_phone("555-SHORT", mock_phone_lookup) == False

    def test_phone_filtering_with_aliases(self):
        """Test phone filtering with filter_numbers_without_aliases enabled."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        
        # Test with alias
        mock_phone_lookup.has_alias.return_value = True
        assert service.should_skip_by_phone("+1234567890", mock_phone_lookup) == False, "Number with alias should not be skipped"
        
        # Test without alias
        mock_phone_lookup.has_alias.return_value = False
        assert service.should_skip_by_phone("+1234567890", mock_phone_lookup) == True, "Number without alias should be skipped"

    def test_phone_filtering_non_phone_numbers(self):
        """Test phone filtering with filter_non_phone_numbers enabled."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_non_phone_numbers=True
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        
        # Test with regular phone number
        assert service.should_skip_by_phone("+1234567890", mock_phone_lookup) == False, "Regular phone number should not be skipped"
        
        # Test with short code (non-phone number)
        assert service.should_skip_by_phone("555-SHORT", mock_phone_lookup) == True, "Short code should be skipped"

    def test_phone_filtering_combined_filters(self):
        """Test phone filtering with multiple filters enabled."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = True
        
        # Test valid phone number with alias
        assert service.should_skip_by_phone("+1234567890", mock_phone_lookup) == False
        
        # Test valid phone number without alias
        mock_phone_lookup.has_alias.return_value = False
        assert service.should_skip_by_phone("+1234567890", mock_phone_lookup) == True
        
        # Test short code (should be skipped regardless of alias)
        mock_phone_lookup.has_alias.return_value = True
        assert service.should_skip_by_phone("555-SHORT", mock_phone_lookup) == True

    def test_combined_filtering_date_and_phone(self):
        """Test combined filtering with both date and phone filters."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = False  # No alias
        
        # Test old message without alias (should be skipped for both reasons)
        old_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        assert service.should_skip_message(old_timestamp, "+1234567890", mock_phone_lookup) == True
        
        # Test current message without alias (should be skipped for phone reason only)
        current_timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        assert service.should_skip_message(current_timestamp, "+1234567890", mock_phone_lookup) == True
        
        # Test current message with alias (should not be skipped)
        mock_phone_lookup.has_alias.return_value = True
        assert service.should_skip_message(current_timestamp, "+1234567890", mock_phone_lookup) == False

    def test_filtering_with_none_phone_lookup_manager(self):
        """Test filtering behavior when phone lookup manager is None."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True
        )
        service = FilteringService(config)
        
        # Should not skip when phone lookup manager is None (can't check for alias)
        assert service.should_skip_by_phone("+1234567890", None) == False

    def test_filtering_with_service_codes(self):
        """Test filtering behavior with service codes."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            include_service_codes=False  # Default: filter out service codes
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        
        # Service codes should be filtered out by default
        assert service.should_skip_by_phone("SERVICE-CODE", mock_phone_lookup) == True
        
        # Test with include_service_codes=True
        config.include_service_codes = True
        service = FilteringService(config)
        assert service.should_skip_by_phone("SERVICE-CODE", mock_phone_lookup) == False

    def test_filtering_with_groups_all_filtered(self):
        """Test filtering behavior with filter_groups_with_all_filtered."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_groups_with_all_filtered=True
        )
        service = FilteringService(config)
        
        # This test would require more complex setup with group filtering logic
        # For now, just verify the config is accessible
        assert service.config.filter_groups_with_all_filtered == True

    def test_filtering_invalid_timestamp(self):
        """Test filtering behavior with invalid timestamp."""
        service = FilteringService(self.base_config)
        
        # Test with invalid timestamp (should not crash)
        invalid_timestamp = -1
        assert service.should_skip_by_date(invalid_timestamp) == False
        
        # Test with very large timestamp
        large_timestamp = 9999999999999999
        assert service.should_skip_by_date(large_timestamp) == False

    def test_filtering_empty_phone_number(self):
        """Test filtering behavior with empty or None phone number."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        
        # Test with empty string
        assert service.should_skip_by_phone("", mock_phone_lookup) == False
        
        # Test with None
        assert service.should_skip_by_phone(None, mock_phone_lookup) == False

    def test_filtering_performance(self):
        """Test that filtering operations are performant."""
        import time
        
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        service = FilteringService(config)
        
        # Mock phone lookup manager
        mock_phone_lookup = Mock()
        mock_phone_lookup.has_alias.return_value = True
        
        # Test 1000 filtering operations
        start_time = time.time()
        for i in range(1000):
            timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
            service.should_skip_message(timestamp, "+1234567890", mock_phone_lookup)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete 1000 operations in less than 1 second
        assert elapsed < 1.0, f"Filtering operations took too long: {elapsed:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
