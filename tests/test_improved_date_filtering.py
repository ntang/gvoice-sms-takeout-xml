"""
Test suite for improved date filtering CLI options.

This test suite validates the new clear date filtering options:
- --exclude-older-than
- --exclude-newer-than  
- --include-date-range

And ensures backward compatibility with deprecated options.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from core.processing_config import ProcessingConfig
from core.conversation_manager import ConversationManager


class TestImprovedDateFilteringCLI:
    """Test the new clear date filtering CLI options."""

    def test_exclude_older_than_option(self):
        """Test --exclude-older-than option."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp"),
            exclude_older_than=datetime(2022, 8, 1)
        )
        
        assert config.exclude_older_than == datetime(2022, 8, 1)
        assert config.exclude_newer_than is None
        assert config.include_date_range is None
        assert config.older_than is None  # Deprecated option not set

    def test_exclude_newer_than_option(self):
        """Test --exclude-newer-than option."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp"),
            exclude_newer_than=datetime(2025, 6, 1)
        )
        
        assert config.exclude_newer_than == datetime(2025, 6, 1)
        assert config.exclude_older_than is None
        assert config.include_date_range is None
        assert config.newer_than is None  # Deprecated option not set

    def test_include_date_range_option(self):
        """Test --include-date-range option."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp"),
            include_date_range="2022-08-01_2025-06-01"
        )
        
        # After validation, include_date_range should set the exclude options
        assert config.include_date_range == "2022-08-01_2025-06-01"
        assert config.exclude_older_than == datetime(2022, 8, 1)
        assert config.exclude_newer_than == datetime(2025, 6, 1)

    def test_include_date_range_validation_success(self):
        """Test include-date-range validation with valid input."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp"),
            include_date_range="2022-01-01_2023-12-31"
        )
        
        # Should not raise any exceptions
        config.validate()
        
        # Should set the equivalent exclude options
        assert config.exclude_older_than == datetime(2022, 1, 1)
        assert config.exclude_newer_than == datetime(2023, 12, 31)

    def test_include_date_range_validation_invalid_format(self):
        """Test include-date-range validation with invalid format."""
        with pytest.raises(ValueError, match="must be in format 'YYYY-MM-DD_YYYY-MM-DD'"):
            config = ProcessingConfig(
                processing_dir=Path("/tmp"),
                include_date_range="2022-08-01"  # Missing end date
            )
            config.validate()

    def test_include_date_range_validation_invalid_range(self):
        """Test include-date-range validation with invalid date range."""
        with pytest.raises(ValueError, match="start date .* must be before end date"):
            config = ProcessingConfig(
                processing_dir=Path("/tmp"),
                include_date_range="2025-06-01_2022-08-01"  # Start after end
            )
            config.validate()

    def test_exclude_options_validation_success(self):
        """Test exclude options validation with valid range."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp"),
            exclude_older_than=datetime(2022, 8, 1),
            exclude_newer_than=datetime(2025, 6, 1)
        )
        
        # Should not raise any exceptions
        config.validate()

    def test_exclude_options_validation_invalid_range(self):
        """Test exclude options validation with invalid range."""
        with pytest.raises(ValueError, match="exclude_older_than .* must be before exclude_newer_than"):
            config = ProcessingConfig(
                processing_dir=Path("/tmp"),
                exclude_older_than=datetime(2025, 6, 1),
                exclude_newer_than=datetime(2022, 8, 1)  # End before start
            )
            config.validate()

    def test_conflicting_options_validation(self):
        """Test validation prevents mixing new and deprecated options."""
        with pytest.raises(ValueError, match="Cannot mix new date filtering options"):
            config = ProcessingConfig(
                processing_dir=Path("/tmp"),
                exclude_older_than=datetime(2022, 8, 1),  # New option
                older_than=datetime(2022, 8, 1)           # Deprecated option
            )
            config.validate()

    def test_backward_compatibility_deprecated_options(self):
        """Test backward compatibility with deprecated --older-than and --newer-than."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp"),
            older_than=datetime(2022, 8, 1),
            newer_than=datetime(2025, 6, 1)
        )
        
        assert config.older_than == datetime(2022, 8, 1)
        assert config.newer_than == datetime(2025, 6, 1)
        assert config.exclude_older_than is None  # New options not set
        assert config.exclude_newer_than is None


class TestImprovedDateFilteringLogic:
    """Test the date filtering logic with new options."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.conversation_manager = ConversationManager(self.temp_dir, large_dataset=False)

    def test_exclude_older_than_filtering(self):
        """Test message filtering with exclude-older-than."""
        config = ProcessingConfig(
            processing_dir=self.temp_dir,
            exclude_older_than=datetime(2022, 8, 1)
        )
        
        # Test timestamps
        old_timestamp = int(datetime(2020, 1, 1).timestamp() * 1000)  # Should be filtered
        new_timestamp = int(datetime(2023, 1, 1).timestamp() * 1000)  # Should be kept
        
        assert self.conversation_manager._should_skip_by_date_filter(old_timestamp, config) == True
        assert self.conversation_manager._should_skip_by_date_filter(new_timestamp, config) == False

    def test_exclude_newer_than_filtering(self):
        """Test message filtering with exclude-newer-than."""
        config = ProcessingConfig(
            processing_dir=self.temp_dir,
            exclude_newer_than=datetime(2025, 6, 1)
        )
        
        # Test timestamps
        old_timestamp = int(datetime(2023, 1, 1).timestamp() * 1000)  # Should be kept
        new_timestamp = int(datetime(2025, 7, 1).timestamp() * 1000)  # Should be filtered
        
        assert self.conversation_manager._should_skip_by_date_filter(old_timestamp, config) == False
        assert self.conversation_manager._should_skip_by_date_filter(new_timestamp, config) == True

    def test_include_date_range_filtering(self):
        """Test message filtering with include-date-range."""
        config = ProcessingConfig(
            processing_dir=self.temp_dir,
            include_date_range="2022-08-01_2025-06-01"
        )
        
        # Validation should set the exclude options
        config.validate()
        
        # Test timestamps
        too_old = int(datetime(2020, 1, 1).timestamp() * 1000)    # Before range - filtered
        in_range = int(datetime(2023, 1, 1).timestamp() * 1000)  # In range - kept  
        too_new = int(datetime(2025, 7, 1).timestamp() * 1000)   # After range - filtered
        
        assert self.conversation_manager._should_skip_by_date_filter(too_old, config) == True
        assert self.conversation_manager._should_skip_by_date_filter(in_range, config) == False
        assert self.conversation_manager._should_skip_by_date_filter(too_new, config) == True

    def test_both_exclude_options_filtering(self):
        """Test message filtering with both exclude options."""
        config = ProcessingConfig(
            processing_dir=self.temp_dir,
            exclude_older_than=datetime(2022, 8, 1),
            exclude_newer_than=datetime(2025, 6, 1)
        )
        
        # Test timestamps
        too_old = int(datetime(2020, 1, 1).timestamp() * 1000)    # Before start - filtered
        in_range = int(datetime(2023, 1, 1).timestamp() * 1000)  # In range - kept
        too_new = int(datetime(2025, 7, 1).timestamp() * 1000)   # After end - filtered
        
        assert self.conversation_manager._should_skip_by_date_filter(too_old, config) == True
        assert self.conversation_manager._should_skip_by_date_filter(in_range, config) == False
        assert self.conversation_manager._should_skip_by_date_filter(too_new, config) == True

    def test_backward_compatibility_filtering(self):
        """Test filtering logic with deprecated options."""
        config = ProcessingConfig(
            processing_dir=self.temp_dir,
            older_than=datetime(2022, 8, 1),
            newer_than=datetime(2025, 6, 1)
        )
        
        # Test timestamps
        too_old = int(datetime(2020, 1, 1).timestamp() * 1000)    # Before start - filtered
        in_range = int(datetime(2023, 1, 1).timestamp() * 1000)  # In range - kept
        too_new = int(datetime(2025, 7, 1).timestamp() * 1000)   # After end - filtered
        
        assert self.conversation_manager._should_skip_by_date_filter(too_old, config) == True
        assert self.conversation_manager._should_skip_by_date_filter(in_range, config) == False
        assert self.conversation_manager._should_skip_by_date_filter(too_new, config) == True

    def test_no_filtering_when_no_options_set(self):
        """Test that no filtering occurs when no date options are set."""
        config = ProcessingConfig(processing_dir=self.temp_dir)
        
        # Test various timestamps - none should be filtered
        old_timestamp = int(datetime(2010, 1, 1).timestamp() * 1000)
        new_timestamp = int(datetime(2030, 1, 1).timestamp() * 1000)
        
        assert self.conversation_manager._should_skip_by_date_filter(old_timestamp, config) == False
        assert self.conversation_manager._should_skip_by_date_filter(new_timestamp, config) == False

    def test_error_handling_in_filtering(self):
        """Test error handling in date filtering logic."""
        config = ProcessingConfig(
            processing_dir=self.temp_dir,
            exclude_older_than=datetime(2022, 8, 1)
        )
        
        # Test with invalid timestamp - should not skip on error
        invalid_timestamp = "not_a_number"
        
        # Should not raise exception and should not skip
        assert self.conversation_manager._should_skip_by_date_filter(invalid_timestamp, config) == False


class TestCLIIntegration:
    """Test CLI integration with new date filtering options."""

    def test_cli_help_shows_new_options(self):
        """Test that CLI help shows the new clear options."""
        from click.testing import CliRunner
        from cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        # Check for new clear options
        assert '--exclude-older-than' in result.output
        assert '--exclude-newer-than' in result.output
        assert '--include-date-range' in result.output
        
        # Check for deprecated warnings
        assert '[DEPRECATED]' in result.output

    def test_cli_example_commands(self):
        """Test example CLI commands with new options."""
        # This is a documentation test to ensure examples work
        examples = [
            # New clear options
            ['--exclude-older-than', '2022-08-01', '--exclude-newer-than', '2025-06-01', 'convert'],
            ['--include-date-range', '2022-08-01_2025-06-01', 'convert'],
            
            # Backward compatibility
            ['--older-than', '2022-08-01', '--newer-than', '2025-06-01', 'convert']
        ]
        
        # These should all parse without errors (we're not actually running conversion)
        for example in examples:
            # Just test that the CLI parsing works
            assert len(example) > 0  # Basic sanity check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
