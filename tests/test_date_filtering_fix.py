"""
TDD test suite for fixing date filtering at message level in conversations.

This test suite follows TDD principles:
1. RED: All tests initially fail 
2. GREEN: Implement minimal code to make tests pass
3. REFACTOR: Clean up implementation while keeping tests passing

Issue: Date filtering works at file level but not within conversation files.
Goal: Ensure conversation files only contain messages within specified date range.
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.conversation_manager import ConversationManager
from core.processing_config import ProcessingConfig


class TestMessageLevelDateFiltering:
    """TDD tests for message-level date filtering in conversation files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path("/tmp/test_conversations")
        self.test_output_dir.mkdir(exist_ok=True)
        
        # Create test dates
        self.old_date = datetime(2015, 1, 1)
        self.recent_date = datetime(2023, 1, 1) 
        self.current_date = datetime(2024, 1, 1)
        
        # Create test timestamps (in milliseconds)
        self.old_timestamp = int(self.old_date.timestamp() * 1000)
        self.recent_timestamp = int(self.recent_date.timestamp() * 1000)
        self.current_timestamp = int(self.current_date.timestamp() * 1000)
        
        # Create test configurations
        self.config_newer_than_2020 = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            newer_than=datetime(2020, 1, 1)
        )
        
        self.config_older_than_2020 = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            older_than=datetime(2020, 1, 1)
        )
        
        self.config_no_filter = ProcessingConfig(
            processing_dir=Path("/tmp/test")
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_write_message_with_content_should_accept_config_parameter(self):
        """FAILING TEST: write_message_with_content should accept config parameter for date filtering."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # This should not raise an exception when config is passed
        try:
            cm.write_message_with_content(
                conversation_id="test_conv",
                timestamp=self.current_timestamp,
                sender="TestSender",
                message="Test message",
                message_type="sms",
                config=self.config_newer_than_2020  # This parameter should be accepted
            )
            success = True
        except TypeError as e:
            if "config" in str(e):
                pytest.fail(f"write_message_with_content should accept config parameter: {e}")
            else:
                raise
        
        assert success

    def test_message_outside_newer_than_filter_should_not_be_written(self):
        """FAILING TEST: Messages older than newer_than filter should not appear in conversation files."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Try to write an old message with newer_than filter
        cm.write_message_with_content(
            conversation_id="test_conv",
            timestamp=self.old_timestamp,  # 2015 message
            sender="TestSender", 
            message="Old message from 2015",
            message_type="sms",
            config=self.config_newer_than_2020  # Filter: newer than 2020
        )
        
        # Finalize to write files
        cm.finalize_conversation_files()
        
        # Check if conversation file was created
        conv_file = self.test_output_dir / "test_conv.html"
        
        if conv_file.exists():
            content = conv_file.read_text()
            # OLD MESSAGE SHOULD NOT APPEAR in conversation file
            assert "Old message from 2015" not in content, "Old message should be filtered out"
        # OR conversation file should not exist at all if no valid messages
        
        # This test should FAIL initially because current implementation doesn't filter at message level

    def test_message_outside_older_than_filter_should_not_be_written(self):
        """FAILING TEST: Messages newer than older_than filter should not appear in conversation files."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Try to write a recent message with older_than filter
        cm.write_message_with_content(
            conversation_id="test_conv",
            timestamp=self.current_timestamp,  # 2024 message
            sender="TestSender",
            message="Recent message from 2024", 
            message_type="sms",
            config=self.config_older_than_2020  # Filter: older than 2020
        )
        
        # Finalize to write files
        cm.finalize_conversation_files()
        
        # Check if conversation file was created
        conv_file = self.test_output_dir / "test_conv.html"
        
        if conv_file.exists():
            content = conv_file.read_text()
            # RECENT MESSAGE SHOULD NOT APPEAR in conversation file
            assert "Recent message from 2024" not in content, "Recent message should be filtered out"
        
        # This test should FAIL initially

    def test_message_within_date_range_should_be_written(self):
        """FAILING TEST: Messages within date range should appear in conversation files."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Write a message within the date range
        cm.write_message_with_content(
            conversation_id="test_conv",
            timestamp=self.recent_timestamp,  # 2023 message
            sender="TestSender",
            message="Valid message from 2023",
            message_type="sms", 
            config=self.config_newer_than_2020  # Filter: newer than 2020 (2023 should pass)
        )
        
        # Finalize to write files
        cm.finalize_conversation_files()
        
        # Conversation file should exist and contain the message
        conv_file = self.test_output_dir / "test_conv.html"
        assert conv_file.exists(), "Conversation file should be created for valid messages"
        
        content = conv_file.read_text()
        assert "Valid message from 2023" in content, "Valid message should appear in conversation"

    def test_conversation_with_no_valid_messages_should_not_be_created(self):
        """FAILING TEST: Conversations with no messages passing date filter should not be created."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Try to write only filtered-out messages
        cm.write_message_with_content(
            conversation_id="empty_conv",
            timestamp=self.old_timestamp,  # 2015 message
            sender="TestSender",
            message="Filtered out message",
            message_type="sms",
            config=self.config_newer_than_2020  # Should filter out 2015 message
        )
        
        # Finalize
        cm.finalize_conversation_files()
        
        # Conversation file should NOT exist
        conv_file = self.test_output_dir / "empty_conv.html"
        assert not conv_file.exists(), "Empty conversation file should not be created"

    def test_mixed_messages_only_valid_ones_appear_in_conversation(self):
        """FAILING TEST: In mixed conversations, only messages passing date filter should appear."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Write multiple messages with different dates
        messages = [
            (self.old_timestamp, "Old message 2015", False),      # Should be filtered out
            (self.recent_timestamp, "Valid message 2023", True),  # Should appear
            (self.current_timestamp, "Current message 2024", True), # Should appear
        ]
        
        for timestamp, message, should_appear in messages:
            cm.write_message_with_content(
                conversation_id="mixed_conv",
                timestamp=timestamp,
                sender="TestSender", 
                message=message,
                message_type="sms",
                config=self.config_newer_than_2020  # Filter: newer than 2020
            )
        
        # Finalize
        cm.finalize_conversation_files()
        
        # Check conversation content
        conv_file = self.test_output_dir / "mixed_conv.html"
        assert conv_file.exists(), "Conversation with valid messages should exist"
        
        content = conv_file.read_text()
        
        # Only valid messages should appear
        assert "Valid message 2023" in content, "2023 message should appear"
        assert "Current message 2024" in content, "2024 message should appear"
        assert "Old message 2015" not in content, "2015 message should be filtered out"

    def test_no_config_means_no_date_filtering(self):
        """FAILING TEST: When no config is provided, all messages should be written (backward compatibility)."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Write messages without config (should all appear)
        cm.write_message_with_content(
            conversation_id="no_filter_conv",
            timestamp=self.old_timestamp,
            sender="TestSender",
            message="Old message without filter",
            message_type="sms"
            # No config parameter - should not filter
        )
        
        cm.finalize_conversation_files()
        
        # Message should appear (backward compatibility)
        conv_file = self.test_output_dir / "no_filter_conv.html"
        assert conv_file.exists()
        content = conv_file.read_text()
        assert "Old message without filter" in content


class TestConversationManagerDateFilteringMethods:
    """TDD tests for new date filtering methods in ConversationManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path("/tmp/test_conversations")
        self.test_output_dir.mkdir(exist_ok=True)
        
        # Fix date range order: older_than must be before newer_than
        self.config_with_filters = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            older_than=datetime(2020, 1, 1),  # Messages before 2020
            newer_than=datetime(2023, 1, 1)   # Messages after 2023
        )
        
        self.config_no_filters = ProcessingConfig(
            processing_dir=Path("/tmp/test")
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_should_skip_by_date_filter_method_should_exist(self):
        """FAILING TEST: ConversationManager should have _should_skip_by_date_filter method."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Method should exist
        assert hasattr(cm, '_should_skip_by_date_filter'), "ConversationManager should have _should_skip_by_date_filter method"
        
        # Method should be callable
        assert callable(getattr(cm, '_should_skip_by_date_filter')), "Method should be callable"

    def test_should_skip_by_date_filter_newer_than_logic(self):
        """FAILING TEST: _should_skip_by_date_filter should correctly apply newer_than filter."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        old_timestamp = int(datetime(2015, 1, 1).timestamp() * 1000)
        new_timestamp = int(datetime(2022, 1, 1).timestamp() * 1000)
        
        # Old message should be skipped
        assert cm._should_skip_by_date_filter(old_timestamp, self.config_with_filters) == True
        
        # New message should not be skipped  
        assert cm._should_skip_by_date_filter(new_timestamp, self.config_with_filters) == False

    def test_should_skip_by_date_filter_older_than_logic(self):
        """FAILING TEST: _should_skip_by_date_filter should correctly apply older_than filter.""" 
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        old_timestamp = int(datetime(2015, 1, 1).timestamp() * 1000)
        new_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        
        # Old message (2015) should be skipped (before older_than=2020)
        assert cm._should_skip_by_date_filter(old_timestamp, self.config_with_filters) == True
        
        # New message (2024) should be skipped (after newer_than=2023)
        assert cm._should_skip_by_date_filter(new_timestamp, self.config_with_filters) == True

    def test_should_skip_by_date_filter_no_config_returns_false(self):
        """FAILING TEST: No config should mean no filtering (backward compatibility)."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        any_timestamp = int(datetime(2015, 1, 1).timestamp() * 1000)
        
        # No config should never skip
        assert cm._should_skip_by_date_filter(any_timestamp, None) == False
        assert cm._should_skip_by_date_filter(any_timestamp, self.config_no_filters) == False


class TestEndToEndDateFilteringIntegration:
    """TDD tests for end-to-end date filtering integration."""

    def setup_method(self):
        """Set up test fixtures.""" 
        self.test_output_dir = Path("/tmp/test_conversations")
        self.test_output_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_sms_processing_should_pass_config_to_conversation_manager(self):
        """FAILING TEST: SMS processing should pass config to write_message_with_content."""
        # This tests the integration between SMS processing and conversation manager
        # Should fail initially because SMS processing doesn't pass config parameter
        
        # Mock the conversation manager to verify config is passed
        mock_cm = Mock()
        
        # We'll need to test that when SMS processing calls write_message_with_content,
        # it passes the config parameter for date filtering
        
        # This test will guide the implementation of config parameter passing
        assert False, "SMS processing integration not implemented yet"

    def test_call_processing_should_pass_config_to_conversation_manager(self):
        """FAILING TEST: Call processing should pass config to write_message_with_content."""
        assert False, "Call processing integration not implemented yet"

    def test_voicemail_processing_should_pass_config_to_conversation_manager(self):
        """FAILING TEST: Voicemail processing should pass config to write_message_with_content."""
        assert False, "Voicemail processing integration not implemented yet"

    def test_conversation_finalization_should_remove_empty_conversations(self):
        """FAILING TEST: finalize_conversation_files should remove conversations with no valid messages."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create a conversation that will be empty after filtering
        cm.conversation_files["empty_conv"] = {
            "file_handle": None,
            "message_count": 0,
            "buffer": []
        }
        
        # This conversation should be removed during finalization if it has no valid messages
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            newer_than=datetime(2020, 1, 1)
        )
        cm.finalize_conversation_files(config=config)
        
        # Conversation file should not exist
        conv_file = self.test_output_dir / "empty_conv.html"
        assert not conv_file.exists(), "Empty conversation should be removed"

    @pytest.mark.integration
    def test_real_dataset_date_filtering_end_to_end(self):
        """FAILING TEST: Real dataset should respect date filtering in conversation files."""
        # This will be an integration test with actual data
        # Should fail initially because current implementation doesn't filter at message level
        
        # Test plan:
        # 1. Run conversion with --newer-than 2020-01-01 on SusanT data
        # 2. Verify SusanT.html only contains messages from 2020 onwards
        # 3. Verify no messages from 2010-2019 appear in the file
        
        assert False, "End-to-end date filtering not implemented yet"


class TestDateFilteringEdgeCases:
    """TDD tests for edge cases in date filtering."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path("/tmp/test_conversations")
        self.test_output_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_invalid_timestamp_should_not_crash_date_filtering(self):
        """FAILING TEST: Invalid timestamps should not crash date filtering."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            newer_than=datetime(2020, 1, 1)
        )
        
        # These should not crash
        invalid_timestamps = [None, -1, 0, "invalid", 999999999999999]
        
        for invalid_ts in invalid_timestamps:
            try:
                cm.write_message_with_content(
                    conversation_id="test_conv",
                    timestamp=invalid_ts,
                    sender="TestSender",
                    message="Test message",
                    message_type="sms",
                    config=config
                )
                # Should not crash, but behavior may vary
            except Exception as e:
                # Should handle gracefully, not crash
                assert "date" not in str(e).lower(), f"Date filtering should handle invalid timestamp gracefully: {e}"

    def test_boundary_date_filtering_precision(self):
        """FAILING TEST: Date filtering should handle boundary conditions precisely."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Test exact boundary dates
        boundary_date = datetime(2020, 1, 1, 0, 0, 0)
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            newer_than=boundary_date
        )
        
        # Message exactly at boundary
        boundary_timestamp = int(boundary_date.timestamp() * 1000)
        
        # Message 1 second before boundary
        before_timestamp = int((boundary_date - timedelta(seconds=1)).timestamp() * 1000)
        
        # Message 1 second after boundary  
        after_timestamp = int((boundary_date + timedelta(seconds=1)).timestamp() * 1000)
        
        # Test boundary behavior (this will define the exact specification)
        assert False, "Boundary date filtering behavior not defined yet"


class TestDateFilteringPerformance:
    """TDD tests for date filtering performance impact."""

    def test_date_filtering_should_not_significantly_impact_performance(self):
        """FAILING TEST: Date filtering should add minimal performance overhead."""
        # This test ensures our implementation is efficient
        assert False, "Performance impact not measured yet"

    def test_filtered_conversations_should_be_smaller_files(self):
        """FAILING TEST: Date filtering should result in smaller conversation files."""
        # Verify that filtering actually reduces file sizes
        assert False, "File size comparison not implemented yet"


# Additional test classes for specific scenarios...

class TestDateFilteringWithExistingFunctionality:
    """TDD tests to ensure date filtering doesn't break existing functionality."""
    
    def test_date_filtering_preserves_call_voicemail_processing(self):
        """FAILING TEST: Date filtering should not break call/voicemail processing."""
        assert False, "Call/voicemail compatibility not tested yet"
    
    def test_date_filtering_preserves_attachment_processing(self):
        """FAILING TEST: Date filtering should not break attachment processing."""
        assert False, "Attachment compatibility not tested yet"
    
    def test_date_filtering_preserves_statistics_accuracy(self):
        """FAILING TEST: Date filtering should maintain accurate statistics."""
        assert False, "Statistics accuracy with filtering not tested yet"


if __name__ == "__main__":
    # Run tests to verify they all fail initially (TDD RED phase)
    pytest.main([__file__, "-v"])
