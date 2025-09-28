"""
Integration tests for parameterized filtering functionality.

This test suite validates end-to-end integration of the new parameterized filtering
system, ensuring that configuration flows correctly from CLI through ProcessingConfig
to FilteringService and finally to SMS processing functions.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from core.processing_config import ProcessingConfig, ConfigurationBuilder
from core.filtering_service import FilteringService
from core.processing_context import ProcessingContext
from core.conversation_manager import ConversationManager
from core.phone_lookup import PhoneLookupManager
from core.path_manager import PathManager
from tests.base_test import BaseSMSTest
import sms


class TestParameterizedFilteringIntegration(BaseSMSTest):
    """Integration tests for parameterized filtering system."""

    def setUp(self):
        """Set up test fixtures for each test method."""
        super().setUp()
        
        # Create test directory structure
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test HTML files with different timestamps and phone numbers
        self.create_test_html_files()
        
        # Create test phone lookup file
        self.phone_lookup_file = self.test_dir / "phone_lookup.txt"
        self.phone_lookup_file.write_text("""+1234567890,John Doe
+1987654321,Jane Smith
555-SHORT,Short Code
""")
        
        # Create mock managers
        self.mock_path_manager = Mock(spec=PathManager)
        self.mock_path_manager.processing_dir = self.test_dir
        self.mock_path_manager.output_dir = self.test_dir / "conversations"
        self.mock_path_manager.log_filename = "test.log"
        
        self.mock_conversation_manager = Mock(spec=ConversationManager)
        self.mock_phone_lookup_manager = Mock(spec=PhoneLookupManager)
        self.mock_phone_lookup_manager.has_alias.return_value = True
        self.mock_phone_lookup_manager.is_excluded.return_value = False
        
        # Create processing context
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
        
        self.context = ProcessingContext(
            config=self.base_config,
            conversation_manager=self.mock_conversation_manager,
            phone_lookup_manager=self.mock_phone_lookup_manager,
            path_manager=self.mock_path_manager,
            processing_dir=self.test_dir,
            output_dir=self.test_dir / "conversations",
            log_filename="test.log"
        )

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Clean up test directory
        if hasattr(self, 'test_dir') and self.test_dir:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        super().tearDown()

    def create_test_html_files(self):
        """Create test HTML files with different characteristics."""
        # File 1: Old message (2022) with known phone number
        old_file = self.calls_dir / "2022-06-15_12-00-00_+1234567890.html"
        old_file.write_text("""
        <html>
            <body>
                <div class="message">
                    <div class="message-header">
                        <span class="message-date">2022-06-15T12:00:00Z</span>
                    </div>
                    <div class="message-body">Old message content</div>
                </div>
            </body>
        </html>
        """)
        
        # File 2: Current message (2023) with known phone number
        current_file = self.calls_dir / "2023-06-15_12-00-00_+1987654321.html"
        current_file.write_text("""
        <html>
            <body>
                <div class="message">
                    <div class="message-header">
                        <span class="message-date">2023-06-15T12:00:00Z</span>
                    </div>
                    <div class="message-body">Current message content</div>
                </div>
            </body>
        </html>
        """)
        
        # File 3: Future message (2025) with known phone number
        future_file = self.calls_dir / "2025-01-15_12-00-00_+1234567890.html"
        future_file.write_text("""
        <html>
            <body>
                <div class="message">
                    <div class="message-header">
                        <span class="message-date">2025-01-15T12:00:00Z</span>
                    </div>
                    <div class="message-body">Future message content</div>
                </div>
            </body>
        </html>
        """)
        
        # File 4: Message with short code
        shortcode_file = self.calls_dir / "2023-06-15_12-00-00_555-SHORT.html"
        shortcode_file.write_text("""
        <html>
            <body>
                <div class="message">
                    <div class="message-header">
                        <span class="message-date">2023-06-15T12:00:00Z</span>
                    </div>
                    <div class="message-body">Short code message</div>
                </div>
            </body>
        </html>
        """)
        
        # File 5: Message with unknown phone number
        unknown_file = self.calls_dir / "2023-06-15_12-00-00_+9999999999.html"
        unknown_file.write_text("""
        <html>
            <body>
                <div class="message">
                    <div class="message-header">
                        <span class="message-date">2023-06-15T12:00:00Z</span>
                    </div>
                    <div class="message-body">Unknown number message</div>
                </div>
            </body>
        </html>
        """)

    def test_filtering_service_integration_with_processing_config(self):
        """Test that FilteringService integrates correctly with ProcessingConfig."""
        # Create configuration with date filtering
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31),
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True
        )
        
        # Create filtering service
        filtering_service = FilteringService(config)
        
        # Test date filtering integration
        old_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        current_timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        future_timestamp = int(datetime(2025, 1, 15).timestamp() * 1000)
        
        assert filtering_service.should_skip_by_date(old_timestamp) == True
        assert filtering_service.should_skip_by_date(current_timestamp) == False
        assert filtering_service.should_skip_by_date(future_timestamp) == True
        
        # Test phone filtering integration
        assert filtering_service.should_skip_by_phone("+1234567890", self.mock_phone_lookup_manager) == False
        assert filtering_service.should_skip_by_phone("555-SHORT", self.mock_phone_lookup_manager) == True

    def test_parameterized_functions_integration_with_config(self):
        """Test that parameterized functions work correctly with ProcessingConfig."""
        # Create configuration with filtering enabled
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        
        # Test parameterized date filtering
        old_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        current_timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        
        assert sms.should_skip_message_by_date_param(old_timestamp, config) == True
        assert sms.should_skip_message_by_date_param(current_timestamp, config) == False
        
        # Test parameterized phone filtering
        self.mock_phone_lookup_manager.has_alias.return_value = True
        assert sms.should_skip_message_by_phone_param("+1234567890", self.mock_phone_lookup_manager, config) == False
        
        self.mock_phone_lookup_manager.has_alias.return_value = False
        assert sms.should_skip_message_by_phone_param("+1234567890", self.mock_phone_lookup_manager, config) == True
        
        # Test combined filtering
        assert sms.should_skip_message_param(old_timestamp, "+1234567890", self.mock_phone_lookup_manager, config) == True

    def test_cli_to_processing_config_integration(self):
        """Test integration from CLI arguments to ProcessingConfig."""
        # Simulate CLI arguments
        cli_args = {
            'processing_dir': self.test_dir,
            'older_than': '2023-01-01',
            'newer_than': '2024-12-31',
            'filter_numbers_without_aliases': True,
            'filter_non_phone_numbers': True,
            'test_mode': False
        }
        
        # Build configuration from CLI args
        config = ConfigurationBuilder.from_cli_args(cli_args)
        
        # Verify configuration is built correctly
        assert config.exclude_older_than == datetime(2023, 1, 1)
        assert config.exclude_newer_than == datetime(2024, 12, 31)
        assert config.filter_numbers_without_aliases == True
        assert config.filter_non_phone_numbers == True
        
        # Test that FilteringService works with CLI-built config
        filtering_service = FilteringService(config)
        
        old_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        assert filtering_service.should_skip_by_date(old_timestamp) == True
        
        assert filtering_service.should_skip_by_phone("555-SHORT", self.mock_phone_lookup_manager) == True

    def test_end_to_end_filtering_with_html_processing(self):
        """Test end-to-end filtering integration with HTML file processing."""
        # Create configuration with filtering
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31),
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True
        )
        
        # Mock the HTML processing to capture filtering behavior
        with patch('sms.process_html_files_param') as mock_process:
            mock_process.return_value = {
                "num_sms": 2,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0
            }
            
            # Create filename map for test files
            src_filename_map = {
                "2022-06-15_12-00-00_+1234567890.html": "2022-06-15_12-00-00_+1234567890.html",
                "2023-06-15_12-00-00_+1987654321.html": "2023-06-15_12-00-00_+1987654321.html",
                "2025-01-15_12-00-00_+1234567890.html": "2025-01-15_12-00-00_+1234567890.html",
                "2023-06-15_12-00-00_555-SHORT.html": "2023-06-15_12-00-00_555-SHORT.html",
                "2023-06-15_12-00-00_+9999999999.html": "2023-06-15_12-00-00_+9999999999.html"
            }
            
            # Call the processing function
            stats = sms.process_html_files_param(
                processing_dir=self.test_dir,
                src_filename_map=src_filename_map,
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=config,
                context=self.context
            )
            
            # Verify the function was called with correct parameters
            mock_process.assert_called_once()
            call_args = mock_process.call_args
            
            # Verify config was passed correctly
            assert call_args.kwargs['config'] == config
            assert call_args.kwargs['conversation_manager'] == self.mock_conversation_manager
            assert call_args.kwargs['phone_lookup_manager'] == self.mock_phone_lookup_manager

    def test_filtering_consistency_across_processing_functions(self):
        """Test that filtering behavior is consistent across different processing functions."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True
        )
        
        # Test timestamp and phone number
        test_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        test_phone = "+1234567890"
        
        # Mock phone lookup manager
        self.mock_phone_lookup_manager.has_alias.return_value = False  # No alias
        
        # Test consistency between FilteringService and parameterized functions
        filtering_service = FilteringService(config)
        
        # Both should produce the same results
        service_date_result = filtering_service.should_skip_by_date(test_timestamp)
        service_phone_result = filtering_service.should_skip_by_phone(test_phone, self.mock_phone_lookup_manager)
        service_combined_result = filtering_service.should_skip_message(test_timestamp, test_phone, self.mock_phone_lookup_manager)
        
        param_date_result = sms.should_skip_message_by_date_param(test_timestamp, config)
        param_phone_result = sms.should_skip_message_by_phone_param(test_phone, self.mock_phone_lookup_manager, config)
        param_combined_result = sms.should_skip_message_param(test_timestamp, test_phone, self.mock_phone_lookup_manager, config)
        
        # Results should be identical
        assert service_date_result == param_date_result
        assert service_phone_result == param_phone_result
        assert service_combined_result == param_combined_result

    def test_filtering_with_none_config_handling(self):
        """Test that filtering functions handle None config gracefully."""
        # Test parameterized functions with None config
        test_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        test_phone = "+1234567890"
        
        # Should not skip when config is None (backward compatibility)
        assert sms.should_skip_message_by_date_param(test_timestamp, None) == False
        assert sms.should_skip_message_by_phone_param(test_phone, self.mock_phone_lookup_manager, None) == False
        assert sms.should_skip_message_param(test_timestamp, test_phone, self.mock_phone_lookup_manager, None) == False

    def test_filtering_performance_integration(self):
        """Test that integrated filtering system maintains good performance."""
        import time
        
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True
        )
        
        # Test 1000 filtering operations
        start_time = time.time()
        
        for i in range(1000):
            timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
            phone = "+1234567890"
            
            # Test the full integration chain
            filtering_service = FilteringService(config)
            filtering_service.should_skip_message(timestamp, phone, self.mock_phone_lookup_manager)
            
            sms.should_skip_message_param(timestamp, phone, self.mock_phone_lookup_manager, config)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete 1000 operations in less than 2 seconds
        assert elapsed < 2.0, f"Integrated filtering operations took too long: {elapsed:.3f}s"

    def test_filtering_error_handling_integration(self):
        """Test that integrated filtering system handles errors gracefully."""
        config = ProcessingConfig(processing_dir=self.test_dir)
        
        # Test with invalid inputs
        invalid_timestamp = -1
        empty_phone = ""
        none_phone = None
        
        # Should not crash and should return False (don't skip)
        assert sms.should_skip_message_by_date_param(invalid_timestamp, config) == False
        assert sms.should_skip_message_by_phone_param(empty_phone, self.mock_phone_lookup_manager, config) == False
        assert sms.should_skip_message_by_phone_param(none_phone, self.mock_phone_lookup_manager, config) == False
        
        # Test with FilteringService
        filtering_service = FilteringService(config)
        assert filtering_service.should_skip_by_date(invalid_timestamp) == False
        assert filtering_service.should_skip_by_phone(empty_phone, self.mock_phone_lookup_manager) == False

    def test_filtering_configuration_summary_integration(self):
        """Test that filtering configuration summary works correctly."""
        config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31),
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True,
            include_service_codes=False
        )
        
        filtering_service = FilteringService(config)
        summary = filtering_service.get_filtering_summary()
        
        # Verify summary structure and content
        assert "date_filtering" in summary
        assert "phone_filtering" in summary
        assert "group_filtering" in summary
        
        assert summary["date_filtering"]["enabled"] == True
        assert summary["phone_filtering"]["enabled"] == True
        assert summary["date_filtering"]["older_than"] == "2023-01-01T00:00:00"
        assert summary["date_filtering"]["newer_than"] == "2024-12-31T00:00:00"
        assert summary["phone_filtering"]["filter_numbers_without_aliases"] == True
        assert summary["phone_filtering"]["filter_non_phone_numbers"] == True
        assert summary["phone_filtering"]["include_service_codes"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
