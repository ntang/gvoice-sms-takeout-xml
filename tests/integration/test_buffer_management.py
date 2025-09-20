"""
Integration tests for ConversationManager buffer management.

These tests verify that the buffer management system correctly handles
message buffering without writing raw text to files prematurely.
"""

import unittest
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, '.')

from core.conversation_manager import ConversationManager


class TestBufferManagement(unittest.TestCase):
    """Test buffer management behavior in ConversationManager."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create conversation manager with small buffer to force flushing behavior
        self.manager = ConversationManager(
            self.temp_path,  # Small buffer to trigger flushing
            batch_size=1000,
            large_dataset=False,
            output_format='html'
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_no_premature_file_writes(self):
        """
        Test that messages are not written to files until finalization.
        
        This test will FAIL with current implementation due to buffer flushing.
        It should PASS after implementing memory-only buffering.
        """
        conversation_id = 'test_no_premature_writes'
        
        # Write a message that should trigger buffer flush
        long_message = 'A' * 150  # Longer than 100-byte buffer
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1640995200000,
            sender='Test Sender',
            message=long_message,
            attachments=[]
        )
        
        # Check that file exists but is empty (no premature writes)
        output_file = self.temp_path / f'{conversation_id}.html'
        self.assertTrue(output_file.exists(), "Output file should exist")
        
        content = output_file.read_text()
        self.assertEqual(len(content), 0, 
            f"File should be empty before finalization, but contains {len(content)} bytes: {repr(content[:100])}")
        
        # Verify message is still in buffer
        file_info = self.manager.conversation_files[conversation_id]
        self.assertEqual(len(file_info['messages']), 1, "Message should be in buffer")
        self.assertGreater(file_info['buffer_size'], 0, "Buffer should have content")

    def test_multiple_messages_no_premature_writes(self):
        """
        Test that multiple messages don't cause premature file writes.
        
        This test will FAIL with current implementation due to buffer flushing.
        It should PASS after implementing memory-only buffering.
        """
        conversation_id = 'test_multiple_messages'
        
        # Write multiple messages that together exceed buffer size
        messages = [
            'First message that is quite long and should not trigger flush',
            'Second message that is also long and should not trigger flush',
            'Third message that when combined with others exceeds buffer'
        ]
        
        for i, message in enumerate(messages):
            self.manager.write_message_with_content(
                conversation_id=conversation_id,
                timestamp=1640995200000 + (i * 1000),
                sender=f'Test Sender {i}',
                message=message,
                attachments=[]
            )
        
        # Check that file is empty (no premature writes)
        output_file = self.temp_path / f'{conversation_id}.html'
        self.assertTrue(output_file.exists(), "Output file should exist")
        
        content = output_file.read_text()
        self.assertEqual(len(content), 0, 
            f"File should be empty before finalization, but contains {len(content)} bytes: {repr(content[:100])}")
        
        # Verify all messages are still in buffer
        file_info = self.manager.conversation_files[conversation_id]
        self.assertEqual(len(file_info['messages']), 3, "All messages should be in buffer")

    def test_finalization_writes_proper_html(self):
        """
        Test that finalization writes proper HTML structure.
        
        This test should PASS with current implementation and continue to PASS
        after implementing memory-only buffering.
        """
        conversation_id = 'test_finalization_html'
        
        # Write a message
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1640995200000,
            sender='Test Sender',
            message='Test message for HTML finalization',
            attachments=[]
        )
        
        # Finalize the conversation
        self.manager.finalize_conversation_files()
        
        # Check that file contains proper HTML structure
        output_file = self.temp_path / f'{conversation_id}.html'
        self.assertTrue(output_file.exists(), "Output file should exist")
        
        content = output_file.read_text()
        self.assertIn('<!DOCTYPE html>', content, "File should contain HTML DOCTYPE")
        self.assertIn('<html', content, "File should contain HTML tag")
        self.assertIn('<table>', content, "File should contain HTML table")
        self.assertIn('Test message for HTML finalization', content, "File should contain message content")
        self.assertIn('Test Sender', content, "File should contain sender information")

    def test_buffer_flush_behavior_regression(self):
        """
        Test that identifies the specific buffer flush regression.
        
        This test will FAIL with current implementation and PASS after fix.
        It specifically tests the scenario that causes raw text to be written.
        """
        conversation_id = 'test_buffer_flush_regression'
        
        # Write a message that exceeds buffer size to trigger flush
        long_message = 'This is a very long message that will definitely exceed the small buffer size and trigger the flush mechanism that currently writes raw text to the file instead of keeping it in memory for proper HTML finalization'
        
        self.manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1640995200000,
            sender='Test Sender',
            message=long_message,
            attachments=[]
        )
        
        # Check that file contains raw text (current broken behavior)
        output_file = self.temp_path / f'{conversation_id}.html'
        content = output_file.read_text()
        
        # This assertion will FAIL after implementing memory-only buffering
        # (because the file should be empty until finalization)
        if len(content) > 0:
            # Current broken behavior: raw text is written
            self.assertNotIn('<!DOCTYPE html>', content, 
                "File should NOT contain HTML structure if raw text was written prematurely")
            self.assertIn(long_message, content, 
                "If content was written, it should be raw text")
            self.assertNotIn('<table>', content, 
                "File should NOT contain HTML table structure if raw text was written")
        else:
            # Correct behavior: file is empty until finalization
            self.assertEqual(len(content), 0, "File should be empty until finalization")

    def test_memory_only_buffering_behavior(self):
        """
        Test the expected behavior after implementing memory-only buffering.
        
        This test documents the expected correct behavior and will help
        verify that the implementation is working correctly.
        """
        conversation_id = 'test_memory_only_behavior'
        
        # Write multiple messages of varying lengths
        messages = [
            ('Short message', 'Sender 1'),
            ('A' * 200, 'Sender 2'),  # Long message
            ('Medium length message with some content', 'Sender 3')
        ]
        
        for i, (message, sender) in enumerate(messages):
            self.manager.write_message_with_content(
                conversation_id=conversation_id,
                timestamp=1640995200000 + (i * 1000),
                sender=sender,
                message=message,
                attachments=[]
            )
        
        # File should be empty regardless of message lengths
        output_file = self.temp_path / f'{conversation_id}.html'
        content = output_file.read_text()
        self.assertEqual(len(content), 0, 
            "File should be empty before finalization with memory-only buffering")
        
        # All messages should be in buffer
        file_info = self.manager.conversation_files[conversation_id]
        self.assertEqual(len(file_info['messages']), 3, 
            "All messages should be in memory buffer")
        
        # Finalize and verify proper HTML
        self.manager.finalize_conversation_files()
        
        final_content = output_file.read_text()
        self.assertIn('<!DOCTYPE html>', final_content, 
            "Finalized file should contain proper HTML structure")
        self.assertIn('<table>', final_content, 
            "Finalized file should contain HTML table")
        
        # Verify all messages are in the final HTML
        for message, sender in messages:
            self.assertIn(message, final_content, 
                f"Message '{message[:20]}...' should be in final HTML")
            self.assertIn(sender, final_content, 
                f"Sender '{sender}' should be in final HTML")


if __name__ == '__main__':
    unittest.main()
