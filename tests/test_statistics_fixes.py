"""
TDD Test Suite for Statistics Tracking Fixes.

This test suite follows TDD principles for fixing the index.html statistics issues:
1. Stats key consistency (sms_count vs num_sms)
2. Message type tracking (SMS vs calls vs voicemails)
3. Latest message time display
4. Attachment counting

RED → GREEN → REFACTOR approach for each fix.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch

from core.conversation_manager import ConversationManager
from core.phone_lookup import PhoneLookupManager


class TestStatsKeyConsistency:
    """TDD tests for fixing stats key consistency issues."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.test_dir / "conversations"
        self.output_dir.mkdir(parents=True)
        
        # Create ConversationManager
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=1024,
            batch_size=100,
            large_dataset=False,
            output_format="html"
        )
        
        # Create PhoneLookupManager
        phone_file = self.test_dir / "phone_lookup.txt"
        self.phone_manager = PhoneLookupManager(phone_file, enable_prompts=False)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_stats_consistency_after_message_write(self):
        """
        RED TEST: Stats should be consistent between write and retrieval methods.
        
        This test will FAIL initially because of key mismatches.
        """
        # Setup: Write a message
        conversation_id = "test_conversation"
        timestamp = int(time.time() * 1000)
        
        # Action: Write message and check stats
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp,
            sender="Test User",
            message="Test message",
            message_type="sms"  # This parameter doesn't exist yet - will fail
        )
        
        # Get stats through both methods
        internal_stats = self.manager.get_total_stats()
        conversation_stats = self.manager._get_conversation_stats_accurate(conversation_id)
        
        # Assert: Internal stats should show the message
        # This will FAIL because of key mismatches
        assert internal_stats["num_sms"] >= 1, f"Internal stats should show SMS message, got {internal_stats}"
        
        # Assert: Conversation stats should show the message
        assert conversation_stats["sms_count"] >= 1, f"Conversation stats should show SMS message, got {conversation_stats}"
    
    def test_different_message_types_tracked_separately(self):
        """
        RED TEST: Different message types should be tracked separately.
        
        This test will FAIL initially because message types aren't distinguished.
        """
        conversation_id = "test_conversation"
        timestamp = int(time.time() * 1000)
        
        # Write different message types
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp,
            sender="Test User", 
            message="SMS message",
            message_type="sms"  # Will fail - parameter doesn't exist
        )
        
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp + 1000,
            sender="Test User",
            message="📞 Call log",
            message_type="call"  # Will fail - parameter doesn't exist
        )
        
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp + 2000,
            sender="Test User",
            message="🎙️ Voicemail",
            message_type="voicemail"  # Will fail - parameter doesn't exist
        )
        
        # Check stats
        stats = self.manager._get_conversation_stats_accurate(conversation_id)
        
        # Assert: Should track different types separately
        # These will FAIL initially
        assert stats["sms_count"] == 1, f"Should have 1 SMS, got {stats['sms_count']}"
        assert stats["calls_count"] == 1, f"Should have 1 call, got {stats['calls_count']}"
        assert stats["voicemails_count"] == 1, f"Should have 1 voicemail, got {stats['voicemails_count']}"


class TestLatestMessageTime:
    """TDD tests for fixing latest message time display."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.test_dir / "conversations"
        self.output_dir.mkdir(parents=True)
        
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=1024,
            batch_size=100,
            large_dataset=False,
            output_format="html"
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_latest_message_time_should_show_actual_timestamp(self):
        """
        RED TEST: Latest message time should show formatted timestamp, not placeholder.
        
        This test will FAIL initially because latest_message_time is hardcoded.
        """
        conversation_id = "test_conversation"
        timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
        
        # Write a message
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp,
            sender="Test User",
            message="Test message"
        )
        
        # Get conversation stats
        stats = self.manager._get_conversation_stats_accurate(conversation_id)
        
        # Assert: Should show actual formatted time, not placeholder
        # This will FAIL initially because latest_message_time is not properly updated
        assert stats["latest_message_time"] != "Latest message data", "Should not show placeholder text"
        assert stats["latest_message_time"] != "No messages", "Should not show default text"
        # Check that it's a properly formatted timestamp (could be local time)
        time_str = str(stats["latest_message_time"])
        assert "2021" in time_str or "2022" in time_str, f"Should contain year 2021 or 2022, got {time_str}"
        assert ":" in time_str, f"Should contain time format, got {time_str}"
    
    def test_conversation_rows_should_use_actual_latest_time(self):
        """
        RED TEST: Conversation table rows should display actual latest message times.
        
        This test will FAIL initially because _build_conversation_rows hardcodes the text.
        """
        conversation_id = "test_conversation"
        timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
        
        # Write a message
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp,
            sender="Test User",
            message="Test message"
        )
        
        # Finalize to create the file
        self.manager.finalize_conversation_files()
        
        # Get conversation files
        conversation_files = list(self.output_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        # Build conversation rows
        rows_html = self.manager._build_conversation_rows(conversation_files)
        
        # Assert: Should contain actual timestamp, not placeholder
        # This will FAIL initially
        assert "Latest message data" not in rows_html, "Should not contain placeholder text"
        # Should contain actual timestamp (could be local time)
        assert "2021" in rows_html or "2022" in rows_html, f"Should contain actual timestamp, got: {rows_html}"
        assert ":" in rows_html, f"Should contain time format, got: {rows_html}"


class TestAttachmentCounting:
    """TDD tests for fixing attachment counting in stats."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.test_dir / "conversations"
        self.output_dir.mkdir(parents=True)
        
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=1024,
            batch_size=100,
            large_dataset=False,
            output_format="html"
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_attachment_count_should_reflect_actual_attachments(self):
        """
        RED TEST: Attachment count should increment when attachments are present.
        
        This test will FAIL initially because attachments aren't counted.
        """
        conversation_id = "test_conversation"
        timestamp = int(time.time() * 1000)
        
        # Write message with attachments
        attachments = [
            "<a href='attachments/photo1.jpg' target='_blank'>📷 Image</a>",
            "<a href='attachments/contact.vcf' target='_blank'>📇 vCard</a>"
        ]
        
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=timestamp,
            sender="Test User",
            message="Message with attachments",
            attachments=attachments
        )
        
        # Check stats
        stats = self.manager._get_conversation_stats_accurate(conversation_id)
        
        # Assert: Should count attachments
        # This will FAIL initially because attachments aren't counted
        assert stats["attachments_count"] == 2, f"Should count 2 attachments, got {stats['attachments_count']}"


class TestStatsIntegration:
    """Integration tests for complete stats functionality."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.test_dir / "conversations"
        self.output_dir.mkdir(parents=True)
        
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=1024,
            batch_size=100,
            large_dataset=False,
            output_format="html"
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_complete_stats_flow_from_write_to_index_generation(self):
        """
        INTEGRATION TEST: Complete flow from message writing to index generation.
        
        This test verifies the entire stats pipeline works correctly.
        """
        # Write various message types
        conversation_id = "integration_test"
        base_timestamp = int(time.time() * 1000)
        
        # SMS message
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=base_timestamp,
            sender="Alice",
            message="Hello world",
            message_type="sms"
        )
        
        # Call log
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=base_timestamp + 1000,
            sender="Alice",
            message="📞 Missed call",
            message_type="call"
        )
        
        # Message with attachment
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=base_timestamp + 2000,
            sender="Alice",
            message="Photo message",
            attachments=["<a href='photo.jpg'>📷 Image</a>"],
            message_type="sms"
        )
        
        # Finalize conversations
        self.manager.finalize_conversation_files()
        
        # Generate index
        test_stats = {"num_sms": 0, "num_calls": 0, "num_voicemails": 0, "num_img": 0, "num_vcf": 0}
        self.manager.generate_index_html(test_stats, 1.5)
        
        # Check index.html content
        index_file = self.output_dir / "index.html"
        assert index_file.exists(), "Index file should be created"
        
        content = index_file.read_text()
        
        # Should show correct stats (using internal stats fallback)
        assert "2" in content, "Should show 2 SMS messages"
        assert "1" in content, "Should show 1 call"
        
        # Should show actual latest message time
        assert "Latest message data" not in content, "Should not show placeholder text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
