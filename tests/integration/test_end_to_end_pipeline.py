"""
End-to-end processing pipeline tests.

These tests will FAIL initially, exposing the critical issue where the complete
conversion pipeline produces empty conversation HTML files despite processing messages.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sms
from tests.base_test import BaseSMSTest


class TestEndToEndProcessingPipeline(BaseSMSTest):
    """Test the complete processing pipeline from HTML input to HTML output."""

    def setUp(self):
        super().setUp()
        self.realistic_html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google Voice - Text</title>
        </head>
        <body>
            <div class="message">
                <cite>+1234567890</cite>
                <q>Hello, this is a test SMS message from a phone number.</q>
                <span class="time">2023-01-01 12:00:00</span>
            </div>
            <div class="message">
                <cite>Me</cite>
                <q>This is my reply to the message.</q>
                <span class="time">2023-01-01 12:01:00</span>
            </div>
            <div class="message">
                <cite>+1234567890</cite>
                <q>Another message with some content to verify it's processed correctly.</q>
                <span class="time">2023-01-01 12:02:00</span>
            </div>
            <div class="message">
                <cite>Me</cite>
                <q>Final message in this conversation thread.</q>
                <span class="time">2023-01-01 12:03:00</span>
            </div>
        </body>
        </html>
        """

    def test_full_conversion_produces_non_empty_files(self):
        """Test that full conversion produces conversation files with content.
        
        This test will FAIL initially because:
        1. Messages are processed but statistics remain 0
        2. Finalization sees 0 statistics and produces empty files
        3. Conversation HTML files end up with 0 bytes
        """
        # Setup: Create test HTML file
        test_file = self.test_dir / "+1234567890 - Text - 2023-01-01T12_00_00Z.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process the HTML file through the complete pipeline
        sms.process_html_files([test_file])
        
        # Action: Finalize conversation files
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Check that conversation files were created
        conversation_files = list(self.test_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        self.assertGreater(
            len(conversation_files),
            0,
            "Should have created conversation HTML files, but none were found. "
            "This indicates the conversation file creation process failed."
        )
        
        # Check that conversation files have content
        for file in conversation_files:
            file_size = file.stat().st_size
            self.assertGreater(
                file_size,
                0,
                f"Conversation file {file.name} should have content, but got {file_size} bytes. "
                "This indicates the finalization process produced empty files, likely due to zero statistics."
            )
            
            # Check file content
            content = file.read_text()
            self.assertGreater(
                len(content),
                100,
                f"Conversation file {file.name} should have substantial content (HTML structure), "
                f"but got only {len(content)} characters. This suggests incomplete HTML generation."
            )

    def test_conversation_file_content_structure(self):
        """Test that conversation files have proper HTML structure and content.
        
        This test will FAIL initially because:
        1. Files are empty (0 bytes) due to zero statistics
        2. No HTML structure is generated
        3. Message content is not present in files
        """
        # Setup: Create test HTML file
        test_file = self.test_dir / "test_conversation.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process and finalize
        sms.process_html_files([test_file])
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Find the generated conversation file
        conversation_files = list(self.test_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        if len(conversation_files) == 0:
            self.fail("No conversation files were created. This indicates complete failure of the conversion process.")
        
        conversation_file = conversation_files[0]
        content = conversation_file.read_text()
        
        # Assert: HTML structure should be present
        self.assertIn(
            "<!DOCTYPE html>",
            content,
            "Conversation file should contain proper HTML DOCTYPE declaration"
        )
        
        self.assertIn(
            "<html",
            content,
            "Conversation file should contain HTML tag"
        )
        
        self.assertIn(
            "<head>",
            content,
            "Conversation file should contain head section"
        )
        
        self.assertIn(
            "<body>",
            content,
            "Conversation file should contain body section"
        )
        
        # Assert: Message content should be present
        self.assertIn(
            "Hello, this is a test SMS message",
            content,
            "Conversation file should contain the first message text"
        )
        
        self.assertIn(
            "This is my reply to the message",
            content,
            "Conversation file should contain the second message text"
        )
        
        self.assertIn(
            "Another message with some content",
            content,
            "Conversation file should contain the third message text"
        )
        
        # Assert: Timestamps should be present
        self.assertIn(
            "2023-01-01 12:00:00",
            content,
            "Conversation file should contain formatted timestamps"
        )
        
        # Assert: Sender information should be present
        self.assertIn(
            "+1234567890",
            content,
            "Conversation file should contain sender phone number"
        )
        
        self.assertIn(
            "Me",
            content,
            "Conversation file should contain 'Me' for sent messages"
        )

    def test_conversation_file_has_proper_table_structure(self):
        """Test that conversation files use proper table structure for messages.
        
        This test will FAIL initially because files are empty and don't contain
        the expected table structure for displaying messages.
        """
        # Setup: Create test HTML file
        test_file = self.test_dir / "test_conversation.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process and finalize
        sms.process_html_files([test_file])
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Find the generated conversation file
        conversation_files = list(self.test_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        if len(conversation_files) == 0:
            self.fail("No conversation files were created.")
        
        conversation_file = conversation_files[0]
        content = conversation_file.read_text()
        
        # Assert: Table structure should be present
        self.assertIn(
            "<table",
            content,
            "Conversation file should contain a table for message display"
        )
        
        self.assertIn(
            "<th>Date/Time</th>",
            content,
            "Conversation file should contain table headers for Date/Time"
        )
        
        self.assertIn(
            "<th>Sender</th>",
            content,
            "Conversation file should contain table headers for Sender"
        )
        
        self.assertIn(
            "<th>Message</th>",
            content,
            "Conversation file should contain table headers for Message"
        )
        
        # Assert: Table rows should be present
        self.assertIn(
            "<tr>",
            content,
            "Conversation file should contain table rows for messages"
        )
        
        # Assert: Table cells should be present
        self.assertIn(
            "<td>",
            content,
            "Conversation file should contain table cells with message data"
        )

    def test_index_html_generation_with_conversations(self):
        """Test that index.html is generated with proper conversation links.
        
        This test will FAIL initially if index.html doesn't properly list
        the conversation files or if conversation files are empty.
        """
        # Setup: Create test HTML file
        test_file = self.test_dir / "test_conversation.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process and finalize
        sms.process_html_files([test_file])
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Generate index.html
        sms.CONVERSATION_MANAGER.generate_index_html(elapsed_time=10.5)
        
        # Check that index.html exists
        index_file = self.test_dir / "index.html"
        self.assertTrue(
            index_file.exists(),
            "index.html should be generated after processing"
        )
        
        # Check index.html content
        index_content = index_file.read_text()
        
        # Assert: Index should contain conversation links
        conversation_files = list(self.test_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        for conv_file in conversation_files:
            self.assertIn(
                conv_file.name,
                index_content,
                f"index.html should contain link to conversation file {conv_file.name}"
            )
        
        # Assert: Index should show non-zero statistics
        self.assertNotIn(
            "Total conversations: 0",
            index_content,
            "index.html should not show zero conversations when files were processed"
        )
        
        self.assertNotIn(
            "SMS Messages</div>\n                <div class=\"stat-number\">0</div>",
            index_content,
            "index.html should not show zero SMS messages when messages were processed"
        )

    def test_processing_statistics_flow(self):
        """Test that processing statistics flow correctly through the pipeline.
        
        This test will FAIL initially because statistics are not updated during
        message processing, leading to zero statistics throughout the pipeline.
        """
        # Setup: Create test HTML file
        test_file = self.test_dir / "test_conversation.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Check initial statistics
        initial_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Action: Process the file
        sms.process_html_files([test_file])
        
        # Check statistics after processing
        after_processing_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Assert: Statistics should have increased
        self.assertGreater(
            after_processing_stats['num_sms'],
            initial_stats['num_sms'],
            "Statistics should increase after processing messages. "
            "This indicates the statistics tracking system is broken."
        )
        
        # Action: Finalize
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Check statistics after finalization
        after_finalization_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Assert: Statistics should remain the same after finalization
        self.assertEqual(
            after_finalization_stats['num_sms'],
            after_processing_stats['num_sms'],
            "Statistics should not change during finalization. "
            "Finalization should only use existing statistics."
        )


if __name__ == '__main__':
    unittest.main()
