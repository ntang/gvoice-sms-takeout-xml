"""
Integration tests for date and phone filtering functionality.

These tests verify that the filtering system works correctly end-to-end,
including CLI integration, configuration processing, and SMS module patching.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from core.processing_config import ProcessingConfig, ConfigurationBuilder
from core.sms_patch import patch_sms_module, unpatch_sms_module
from tests.base_test import BaseSMSTest


class TestFilteringIntegration(BaseSMSTest):
    """Integration tests for filtering functionality."""

    def setUp(self):
        """Set up test fixtures for each test method."""
        super().setUp()
        
        # Create test directory structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test HTML file
        self.test_file = self.calls_dir / "test_message.html"
        self.test_file.write_text("""
        <html>
            <body>
                <div class="message">
                    <div class="message-header">
                        <span class="message-date">2023-06-15T12:00:00Z</span>
                    </div>
                    <div class="message-body">Test message content</div>
                </div>
            </body>
        </html>
        """)
        
        self.patcher = None

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Clean up patcher if it exists
        if hasattr(self, 'patcher') and self.patcher:
            try:
                unpatch_sms_module(self.patcher)
            except Exception as e:
                print(f"Warning: Failed to unpatch SMS module: {e}")
        
        # Clean up test directory
        if hasattr(self, 'test_dir') and self.test_dir:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        
        super().tearDown()

    def test_date_filtering_configuration_integration(self):
        """Test that date filtering configuration is properly applied."""
        # Create configuration with date filters
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31)
        )
        
        # Patch SMS module
        self.patcher = patch_sms_module(config)
        
        try:
            import sms
            
            # Verify global variables are set
            assert sms.DATE_FILTER_OLDER_THAN == datetime(2023, 1, 1)
            assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 12, 31)
            
            # Test filtering logic
            old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
            current_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
            future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
            
            assert sms.should_skip_message_by_date(old_timestamp), "Old message should be skipped"
            assert not sms.should_skip_message_by_date(current_timestamp), "Current message should not be skipped"
            assert sms.should_skip_message_by_date(future_timestamp), "Future message should be skipped"
            
        finally:
            unpatch_sms_module(self.patcher)
            self.patcher = None

    def test_phone_filtering_configuration_integration(self):
        """Test that phone filtering configuration is properly applied."""
        # Create configuration with phone filters
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True,
            skip_filtered_contacts=True,
            include_service_codes=False
        )
        
        # Patch SMS module
        self.patcher = patch_sms_module(config)
        
        try:
            import sms
            
            # Verify global variables are set
            assert sms.FILTER_NUMBERS_WITHOUT_ALIASES == True
            assert sms.FILTER_NON_PHONE_NUMBERS == True
            assert sms.SKIP_FILTERED_CONTACTS == True
            assert sms.INCLUDE_SERVICE_CODES == False
            
        finally:
            unpatch_sms_module(self.patcher)
            self.patcher = None

    def test_cli_date_filtering_integration(self):
        """Test that CLI date filtering arguments are properly processed."""
        # Simulate CLI arguments
        cli_args = {
            'processing_dir': self.test_dir,
            'older_than': '2023-01-01',
            'newer_than': '2024-12-31',
            'test_mode': False
        }
        
        # Build configuration from CLI args
        config = ConfigurationBuilder.from_cli_args(cli_args)
        
        # Patch SMS module
        self.patcher = patch_sms_module(config)
        
        try:
            import sms
            
            # Verify CLI arguments were processed correctly
            assert sms.DATE_FILTER_OLDER_THAN == datetime(2023, 1, 1)
            assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 12, 31)
            
            # Test filtering works with CLI-set values
            old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
            assert sms.should_skip_message_by_date(old_timestamp), "CLI-set filter should work"
            
        finally:
            unpatch_sms_module(self.patcher)
            self.patcher = None

    def test_cli_phone_filtering_integration(self):
        """Test that CLI phone filtering arguments are properly processed."""
        # Simulate CLI arguments
        cli_args = {
            'processing_dir': self.test_dir,
            'filter_numbers_without_aliases': True,
            'filter_non_phone_numbers': False,
            'skip_filtered_contacts': True,
            'include_service_codes': True
        }
        
        # Build configuration from CLI args
        config = ConfigurationBuilder.from_cli_args(cli_args)
        
        # Patch SMS module
        self.patcher = patch_sms_module(config)
        
        try:
            import sms
            
            # Verify CLI arguments were processed correctly
            assert sms.FILTER_NUMBERS_WITHOUT_ALIASES == True
            assert sms.FILTER_NON_PHONE_NUMBERS == False
            assert sms.SKIP_FILTERED_CONTACTS == True
            assert sms.INCLUDE_SERVICE_CODES == True
            
        finally:
            unpatch_sms_module(self.patcher)
            self.patcher = None

    def test_shared_constants_consistency(self):
        """Test that shared_constants module is updated consistently."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        
        # Patch SMS module
        self.patcher = patch_sms_module(config)
        
        try:
            import sms
            from core import shared_constants
            
            # Verify both modules have the same values
            assert sms.DATE_FILTER_OLDER_THAN == shared_constants.DATE_FILTER_OLDER_THAN
            assert sms.FILTER_NUMBERS_WITHOUT_ALIASES == shared_constants.FILTER_NUMBERS_WITHOUT_ALIASES
            
        finally:
            unpatch_sms_module(self.patcher)
            self.patcher = None

    def test_filtering_edge_cases(self):
        """Test filtering edge cases and error conditions."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=None,  # No older filter
            exclude_newer_than=datetime(2024, 12, 31)  # Only newer filter
        )
        
        # Patch SMS module
        self.patcher = patch_sms_module(config)
        
        try:
            import sms
            
            # Test with no older filter
            assert sms.DATE_FILTER_OLDER_THAN is None
            assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 12, 31)
            
            # Test filtering with only newer filter
            old_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
            future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
            
            assert not sms.should_skip_message_by_date(old_timestamp), "Old message should not be skipped with no older filter"
            assert sms.should_skip_message_by_date(future_timestamp), "Future message should be skipped with newer filter"
            
        finally:
            unpatch_sms_module(self.patcher)
            self.patcher = None

    def test_filtering_with_invalid_dates(self):
        """Test filtering behavior with invalid date configurations."""
        # Test with invalid date range (older > newer)
        with pytest.raises(ValueError, match="exclude_older_than.*must be before.*exclude_newer_than"):
            ProcessingConfig(
                processing_dir=self.test_dir,
                exclude_older_than=datetime(2024, 1, 1),
                exclude_newer_than=datetime(2023, 12, 31)  # Invalid: newer is before older
            )

    def test_filtering_restoration_after_unpatch(self):
        """Test that filtering values are properly restored after unpatching."""
        # Get original values
        import sms
        original_older = sms.DATE_FILTER_OLDER_THAN
        original_newer = sms.DATE_FILTER_NEWER_THAN
        
        # Apply configuration
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31)
        )
        
        self.patcher = patch_sms_module(config)
        
        try:
            # Verify values are changed
            assert sms.DATE_FILTER_OLDER_THAN == datetime(2023, 1, 1)
            assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 12, 31)
            
        finally:
            # Restore original values
            unpatch_sms_module(self.patcher)
            self.patcher = None
            
            # Verify values are restored
            assert sms.DATE_FILTER_OLDER_THAN == original_older
            assert sms.DATE_FILTER_NEWER_THAN == original_newer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
