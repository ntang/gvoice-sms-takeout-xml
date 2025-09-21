"""
Message processing statistics tests.

These tests will FAIL initially, exposing the critical issue where individual
message processing methods don't update statistics correctly.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sms
from core.conversation_manager import ConversationManager
from tests.base_test import BaseSMSTest


class TestMessageProcessingStatistics(BaseSMSTest):
    """Test that individual message processing updates statistics correctly."""

    def setUp(self):
        super().setUp()
        # Create a mock phone lookup manager
        self.mock_phone_lookup = Mock()
        self.mock_phone_lookup.get_alias.return_value = "Test User"
        
        # Create a mock path manager
        self.mock_path_manager = Mock()

    def test_write_message_with_content_updates_statistics(self):
        """Test that write_message_with_content increments statistics.
        
        This test will FAIL initially because:
        1. write_message_with_content() doesn't increment conversation_stats['sms_count']
        2. Statistics remain at 0 even after processing messages
        3. This is the root cause of the empty HTML files issue
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        # Check initial statistics
        initial_stats = conversation_manager.get_total_stats()
        initial_sms_count = initial_stats['num_sms']
        
        # Check initial conversation stats
        initial_conv_stats = conversation_manager.conversation_stats.get(conversation_id, {})
        initial_conv_sms_count = initial_conv_stats.get('sms_count', 0)
        
        # Action: Write a message
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574400000,
            sender="Test User",
            message="This is a test message"
        )
        
        # Assert: Conversation stats should be updated
        updated_conv_stats = conversation_manager.conversation_stats.get(conversation_id, {})
        updated_conv_sms_count = updated_conv_stats.get('sms_count', 0)
        
        self.assertGreater(
            updated_conv_sms_count,
            initial_conv_sms_count,
            f"Conversation stats 'sms_count' should increase from {initial_conv_sms_count} "
            f"to {updated_conv_sms_count + 1} after writing a message. "
            "This indicates write_message_with_content() is not updating conversation_stats."
        )
        
        # Assert: Total stats should be updated
        updated_total_stats = conversation_manager.get_total_stats()
        updated_total_sms_count = updated_total_stats['num_sms']
        
        self.assertGreater(
            updated_total_sms_count,
            initial_sms_count,
            f"Total stats 'num_sms' should increase from {initial_sms_count} "
            f"to {updated_total_sms_count + 1} after writing a message. "
            "This indicates the statistics aggregation is not working."
        )
        
        # Assert: Statistics should be synchronized
        self.assertEqual(
            updated_total_sms_count,
            updated_conv_sms_count,
            f"Total stats 'num_sms' ({updated_total_sms_count}) should equal "
            f"conversation stats 'sms_count' ({updated_conv_sms_count}). "
            "This indicates the statistics are not synchronized."
        )

    def test_multiple_messages_update_statistics_correctly(self):
        """Test that processing multiple messages updates statistics correctly.
        
        This test will FAIL initially because each message doesn't increment
        the statistics, so the final count will be 0 instead of the expected count.
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        num_messages = 5
        
        # Action: Write multiple messages
        for i in range(num_messages):
            conversation_manager.write_message_with_content(
                conversation_id=conversation_id,
                timestamp=1672574400000 + (i * 60000),  # 1 minute apart
                sender=f"User {i}",
                message=f"Test message {i}"
            )
        
        # Check final statistics
        final_stats = conversation_manager.get_total_stats()
        final_conv_stats = conversation_manager.conversation_stats.get(conversation_id, {})
        
        # Assert: Should have processed all messages
        self.assertEqual(
            final_stats['num_sms'],
            num_messages,
            f"Should have processed {num_messages} messages, but total stats show {final_stats['num_sms']}. "
            "This indicates write_message_with_content() is not incrementing statistics."
        )
        
        self.assertEqual(
            final_conv_stats.get('sms_count', 0),
            num_messages,
            f"Should have processed {num_messages} messages, but conversation stats show {final_conv_stats.get('sms_count', 0)}. "
            "This indicates conversation_stats['sms_count'] is not being updated."
        )

    def test_statistics_updated_before_finalization(self):
        """Test that statistics are updated before finalization begins.
        
        This test will FAIL initially because statistics are never updated during
        message processing, so they remain 0 before finalization.
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        # Action: Write messages but don't finalize yet
        for i in range(3):
            conversation_manager.write_message_with_content(
                conversation_id=conversation_id,
                timestamp=1672574400000 + (i * 60000),
                sender="Test User",
                message=f"Message {i}"
            )
        
        # Check statistics before finalization
        stats_before_finalization = conversation_manager.get_total_stats()
        
        # Assert: Statistics should already be updated
        self.assertGreater(
            stats_before_finalization['num_sms'],
            0,
            f"Statistics should be updated before finalization, but got {stats_before_finalization['num_sms']}. "
            "This indicates statistics are not being updated during message processing."
        )
        
        # Action: Finalize
        conversation_manager.finalize_conversation_files()
        
        # Check statistics after finalization
        stats_after_finalization = conversation_manager.get_total_stats()
        
        # Assert: Statistics should not change during finalization
        self.assertEqual(
            stats_after_finalization['num_sms'],
            stats_before_finalization['num_sms'],
            "Statistics should not change during finalization. "
            "Finalization should only use pre-existing statistics."
        )

    def test_statistics_atomicity(self):
        """Test that statistics updates are atomic (all-or-nothing).
        
        This test will FAIL if statistics updates are not atomic, leading to
        inconsistent state between conversation_stats and total_stats.
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        # Action: Write a message
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574400000,
            sender="Test User",
            message="Test message"
        )
        
        # Check both conversation and total statistics
        conv_stats = conversation_manager.conversation_stats.get(conversation_id, {})
        total_stats = conversation_manager.get_total_stats()
        
        # Assert: Both should be updated consistently
        conv_sms_count = conv_stats.get('sms_count', 0)
        total_sms_count = total_stats['num_sms']
        
        self.assertEqual(
            conv_sms_count,
            total_sms_count,
            f"Conversation stats 'sms_count' ({conv_sms_count}) should equal "
            f"total stats 'num_sms' ({total_sms_count}). "
            "This indicates statistics updates are not atomic."
        )
        
        # Both should be greater than 0 if the update worked
        if conv_sms_count > 0:
            self.assertGreater(
                total_sms_count,
                0,
                "If conversation stats are updated, total stats should also be updated"
            )
        else:
            self.assertEqual(
                total_sms_count,
                0,
                "If conversation stats are not updated, total stats should also be 0"
            )

    def test_statistics_with_different_conversation_types(self):
        """Test that statistics work correctly with different conversation types.
        
        This test will FAIL if statistics tracking doesn't work for different
        types of conversations or if the conversation ID generation is broken.
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        # Test different conversation types
        conversations = [
            ("+1234567890", "Phone number conversation"),
            ("TestUser", "Named conversation"),
            ("Group_Conversation", "Group conversation")
        ]
        
        messages_per_conversation = 2
        
        # Action: Write messages to different conversations
        for conv_id, description in conversations:
            for i in range(messages_per_conversation):
                conversation_manager.write_message_with_content(
                    conversation_id=conv_id,
                    timestamp=1672574400000 + (i * 60000),
                    sender="Test User",
                    message=f"Message {i} in {description}"
                )
        
        # Check statistics
        total_stats = conversation_manager.get_total_stats()
        conversation_stats = conversation_manager.conversation_stats
        
        # Assert: Should have processed messages for all conversations
        expected_total = len(conversations) * messages_per_conversation
        self.assertEqual(
            total_stats['num_sms'],
            expected_total,
            f"Should have processed {expected_total} messages across {len(conversations)} conversations, "
            f"but got {total_stats['num_sms']}. This indicates statistics tracking is broken "
            "for multiple conversations."
        )
        
        # Assert: Each conversation should have its own stats
        self.assertEqual(
            len(conversation_stats),
            len(conversations),
            f"Should have stats for {len(conversations)} conversations, "
            f"but got {len(conversation_stats)}. This indicates conversation stats "
            "are not being created for each conversation."
        )
        
        # Assert: Each conversation should have correct message count
        for conv_id, description in conversations:
            conv_stats = conversation_stats.get(conv_id, {})
            conv_sms_count = conv_stats.get('sms_count', 0)
            
            self.assertEqual(
                conv_sms_count,
                messages_per_conversation,
                f"Conversation '{conv_id}' ({description}) should have {messages_per_conversation} "
                f"messages, but stats show {conv_sms_count}. This indicates statistics "
                "are not being tracked per conversation."
            )

    def test_statistics_error_handling(self):
        """Test that statistics tracking handles errors gracefully.
        
        This test will FAIL if statistics tracking doesn't handle errors properly,
        leading to inconsistent state or crashes.
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        # Action: Write a valid message first
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574400000,
            sender="Test User",
            message="Valid message"
        )
        
        # Check statistics after valid message
        stats_after_valid = conversation_manager.get_total_stats()
        
        # Action: Try to write a message with invalid data
        try:
            conversation_manager.write_message_with_content(
                conversation_id=conversation_id,
                timestamp=None,  # Invalid timestamp
                sender="Test User",
                message="Invalid message"
            )
        except Exception:
            # Expected to fail, but statistics should remain consistent
            pass
        
        # Check statistics after error
        stats_after_error = conversation_manager.get_total_stats()
        
        # Assert: Statistics should remain consistent even after errors
        self.assertGreaterEqual(
            stats_after_error['num_sms'],
            stats_after_valid['num_sms'],
            "Statistics should not decrease after errors. "
            "This indicates statistics tracking is not handling errors gracefully."
        )
        
        # The statistics should be the same or greater (if the invalid message was still processed)
        # but should never be inconsistent or cause the system to crash


if __name__ == '__main__':
    unittest.main()
