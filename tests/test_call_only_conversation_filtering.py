"""
TDD Test Suite for Call-Only Conversation Filtering

This test suite validates filtering out conversations that contain only call records
(no SMS/MMS/voicemail text content) by default, with option to include them.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime

from core.processing_config import ProcessingConfig
from core.conversation_manager import ConversationManager


class TestCallOnlyConversationFiltering:
    """TDD tests for call-only conversation filtering (default enabled)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_call_only_conversations_filtered_by_default(self):
        """FAILING TEST: Call-only conversations should be filtered out by default."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create config first
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False  # Default: filter them out
        )
        
        # Create a conversation with only call records
        cm.write_message_with_content(
            conversation_id="call_only_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="📞 Outgoing call to TestContact (Duration: 30s)",
            message_type="call",
            config=config  # Pass config for content tracking
        )
        
        # Finalize conversations
        cm.finalize_conversation_files(config=config)
        
        # Call-only conversation should NOT exist
        call_only_file = self.test_output_dir / "call_only_conv.html"
        assert not call_only_file.exists(), "Call-only conversations should be filtered out by default"

    def test_include_call_only_conversations_flag_preserves_them(self):
        """FAILING TEST: --include-call-only-conversations flag should preserve call-only conversations."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create config with call-only conversations enabled
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=True  # Explicitly include them
        )
        
        # Create a conversation with only call records
        cm.write_message_with_content(
            conversation_id="preserved_call_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="📞 Incoming call from TestContact (Duration: 45s)",
            message_type="call",
            config=config  # Pass config for content tracking
        )
        
        # Finalize conversations
        cm.finalize_conversation_files(config=config)
        
        # Call-only conversation SHOULD exist
        call_only_file = self.test_output_dir / "preserved_call_conv.html"
        assert call_only_file.exists(), "Call-only conversations should be preserved when flag is enabled"

    def test_conversation_with_mixed_content_always_kept(self):
        """FAILING TEST: Conversations with both calls and text should always be preserved."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create a conversation with both SMS and calls
        cm.write_message_with_content(
            conversation_id="mixed_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="Hello there!",
            message_type="sms"
        )
        
        cm.write_message_with_content(
            conversation_id="mixed_conv",
            timestamp=int(datetime(2023, 1, 2).timestamp() * 1000),
            sender="TestContact",
            message="📞 Outgoing call to TestContact (Duration: 30s)",
            message_type="call"
        )
        
        # Create config with default filtering (should NOT filter mixed conversations)
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        # Finalize conversations
        cm.finalize_conversation_files(config=config)
        
        # Mixed conversation SHOULD exist
        mixed_file = self.test_output_dir / "mixed_conv.html"
        assert mixed_file.exists(), "Mixed conversations should always be preserved"
        
        # Should contain both SMS and call
        content = mixed_file.read_text()
        assert "Hello there!" in content, "Should contain SMS content"
        assert "📞 Outgoing call" in content, "Should contain call content"

    def test_conversation_with_sms_always_kept(self):
        """FAILING TEST: Conversations with SMS should always be preserved regardless of filtering."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create SMS-only conversation
        cm.write_message_with_content(
            conversation_id="sms_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="This is an SMS message",
            message_type="sms"
        )
        
        # Test with call-only filtering enabled (default)
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        cm.finalize_conversation_files(config=config)
        
        # SMS conversation should exist
        sms_file = self.test_output_dir / "sms_conv.html"
        assert sms_file.exists(), "SMS conversations should always be preserved"

    def test_voicemail_with_transcription_should_be_kept(self):
        """FAILING TEST: Voicemails with transcription content should be preserved."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create voicemail with transcription
        cm.write_message_with_content(
            conversation_id="vm_text_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="🎙️ Voicemail from TestContact: Please call me back when you get this message",
            message_type="voicemail"
        )
        
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        cm.finalize_conversation_files(config=config)
        
        # Voicemail with text should be preserved
        vm_file = self.test_output_dir / "vm_text_conv.html"
        assert vm_file.exists(), "Voicemails with transcription should be preserved"

    def test_voicemail_without_transcription_should_be_filtered(self):
        """FAILING TEST: Voicemails without transcription should be treated like calls."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create voicemail without transcription (just entry marker)
        cm.write_message_with_content(
            conversation_id="vm_no_text_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="[Voicemail entry]",  # No actual transcription
            message_type="voicemail"
        )
        
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        cm.finalize_conversation_files(config=config)
        
        # Voicemail without text should be filtered out
        vm_file = self.test_output_dir / "vm_no_text_conv.html"
        assert not vm_file.exists(), "Voicemails without transcription should be filtered like calls"

    def test_mms_conversations_always_kept(self):
        """FAILING TEST: MMS conversations should always be preserved."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create MMS conversation
        cm.write_message_with_content(
            conversation_id="mms_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="Check out this photo!",
            message_type="sms",  # MMS messages use "sms" type
            attachments=["image.jpg"]
        )
        
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        cm.finalize_conversation_files(config=config)
        
        # MMS conversation should exist
        mms_file = self.test_output_dir / "mms_conv.html"
        assert mms_file.exists(), "MMS conversations should always be preserved"


class TestConversationContentTracking:
    """TDD tests for conversation content type tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_track_conversation_content_type_method_should_exist(self):
        """FAILING TEST: ConversationManager should have _track_conversation_content_type method."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Method should exist
        assert hasattr(cm, '_track_conversation_content_type'), "ConversationManager should have _track_conversation_content_type method"

    def test_is_call_only_conversation_method_should_exist(self):
        """FAILING TEST: ConversationManager should have _is_call_only_conversation method."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Method should exist
        assert hasattr(cm, '_is_call_only_conversation'), "ConversationManager should have _is_call_only_conversation method"

    def test_conversation_content_types_tracking(self):
        """FAILING TEST: Should track different content types in conversations."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        # Write different message types
        cm.write_message_with_content(
            conversation_id="test_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TestContact",
            message="SMS message",
            message_type="sms",
            config=config
        )
        
        cm.write_message_with_content(
            conversation_id="test_conv",
            timestamp=int(datetime(2023, 1, 2).timestamp() * 1000),
            sender="TestContact",
            message="📞 Call record",
            message_type="call",
            config=config
        )
        
        # Should track content types
        assert hasattr(cm, 'conversation_content_types'), "Should have conversation_content_types tracking"
        assert "test_conv" in cm.conversation_content_types, "Should track content for test_conv"
        
        content_info = cm.conversation_content_types["test_conv"]
        assert content_info["has_sms"] == True, "Should detect SMS content"
        assert content_info["has_calls_only"] == False, "Should detect mixed content (not call-only)"


class TestCLIIntegration:
    """TDD tests for CLI integration of call-only conversation filtering."""

    def test_cli_should_accept_include_call_only_conversations_flag(self):
        """FAILING TEST: CLI should accept --include-call-only-conversations flag."""
        # This test will guide the CLI implementation
        import subprocess
        
        # Test CLI help includes the new option
        result = subprocess.run(
            ["python", "cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/Users/nicholastang/gvoice-sms-takeout-xml"
        )
        
        assert "--include-call-only-conversations" in result.stdout, "CLI should accept --include-call-only-conversations flag"

    def test_processing_config_should_have_include_call_only_conversations_field(self):
        """FAILING TEST: ProcessingConfig should have include_call_only_conversations field."""
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        
        # Should have the field with default False
        assert hasattr(config, 'include_call_only_conversations'), "ProcessingConfig should have include_call_only_conversations field"
        assert config.include_call_only_conversations == False, "Default should be False (filter call-only conversations)"


class TestEndToEndCallOnlyFiltering:
    """Integration tests for complete call-only conversation filtering workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_complete_filtering_workflow_with_mixed_conversations(self):
        """FAILING TEST: Complete workflow should filter call-only, preserve text conversations."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create multiple conversation types
        
        # 1. Call-only conversation (should be filtered)
        cm.write_message_with_content(
            conversation_id="calls_only",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="CallContact",
            message="📞 Outgoing call (Duration: 30s)",
            message_type="call"
        )
        
        # 2. SMS conversation (should be kept)
        cm.write_message_with_content(
            conversation_id="text_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="TextContact",
            message="Hello there!",
            message_type="sms"
        )
        
        # 3. Mixed conversation (should be kept)
        cm.write_message_with_content(
            conversation_id="mixed_conv",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="MixedContact",
            message="Text message",
            message_type="sms"
        )
        cm.write_message_with_content(
            conversation_id="mixed_conv",
            timestamp=int(datetime(2023, 1, 2).timestamp() * 1000),
            sender="MixedContact",
            message="📞 Call record",
            message_type="call"
        )
        
        # Default config (should filter call-only)
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        cm.finalize_conversation_files(config=config)
        
        # Verify filtering results
        assert not (self.test_output_dir / "calls_only.html").exists(), "Call-only conversation should be filtered"
        assert (self.test_output_dir / "text_conv.html").exists(), "SMS conversation should be preserved"
        assert (self.test_output_dir / "mixed_conv.html").exists(), "Mixed conversation should be preserved"

    def test_conversation_statistics_should_reflect_filtering(self):
        """FAILING TEST: Conversation statistics should reflect call-only filtering."""
        cm = ConversationManager(output_dir=self.test_output_dir, large_dataset=False)
        
        # Create conversations that will be filtered
        cm.write_message_with_content(
            conversation_id="call1",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="Contact1",
            message="📞 Call record",
            message_type="call"
        )
        
        cm.write_message_with_content(
            conversation_id="sms1",
            timestamp=int(datetime(2023, 1, 1).timestamp() * 1000),
            sender="Contact2",
            message="SMS message",
            message_type="sms"
        )
        
        config = ProcessingConfig(
            processing_dir=self.test_output_dir,
            include_call_only_conversations=False
        )
        
        cm.finalize_conversation_files(config=config)
        
        # Statistics should reflect filtering
        total_stats = cm.get_total_stats()
        
        # Should show only 1 conversation (SMS), not 2
        # This test will initially fail because filtering isn't implemented
        assert False, "Statistics tracking for call-only filtering not implemented yet"
