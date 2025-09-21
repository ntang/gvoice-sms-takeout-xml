"""
End-to-end statistics synchronization tests.

These tests will FAIL initially, exposing the critical issue where the complete
conversion pipeline uses incorrect statistics, leading to empty HTML files and
incorrect final summaries.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sms
from tests.base_test import BaseSMSTest


class TestStatisticsSynchronization(BaseSMSTest):
    """Test that statistics are synchronized correctly throughout the entire pipeline."""

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

    def test_complete_pipeline_statistics_flow(self):
        """Test that statistics flow correctly through the complete conversion pipeline.
        
        This test will FAIL initially because:
        1. process_html_files() returns zero statistics
        2. Final summary uses these zero statistics
        3. HTML files are empty because finalization sees zero statistics
        """
        # Setup: Create Calls directory structure
        calls_dir = self.test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup: Create test HTML file
        test_file = calls_dir / "+1234567890 - Text - 2023-01-01T12_00_00Z.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process the HTML file through the complete pipeline
        file_mapping = {str(test_file): str(test_file)}
        process_stats = sms.process_html_files(file_mapping)
        
        # Action: Finalize conversation files
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Action: Generate index.html
        sms.CONVERSATION_MANAGER.generate_index_html(process_stats, 10.5)
        
        # Get final statistics from ConversationManager
        final_cm_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Assert: process_html_files() should return non-zero statistics
        self.assertGreater(
            process_stats['num_sms'],
            0,
            f"process_html_files() should return non-zero statistics when messages are processed. "
            f"Got {process_stats['num_sms']} SMS messages. This indicates the statistics "
            "are not being retrieved from ConversationManager."
        )
        
        # Assert: Statistics should be consistent between process_html_files() and ConversationManager
        self.assertEqual(
            process_stats['num_sms'],
            final_cm_stats['num_sms'],
            f"process_html_files() returned {process_stats['num_sms']} SMS messages, "
            f"but ConversationManager shows {final_cm_stats['num_sms']}. "
            "This indicates a statistics synchronization failure."
        )
        
        # Assert: HTML files should have content
        conversation_files = list(self.test_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        self.assertGreater(
            len(conversation_files),
            0,
            "Should have created conversation HTML files"
        )
        
        for file in conversation_files:
            file_size = file.stat().st_size
            self.assertGreater(
                file_size,
                0,
                f"Conversation file {file.name} should have content when statistics are non-zero, "
                f"but got {file_size} bytes. This indicates finalization is not working correctly."
            )
            
            # Check file content
            content = file.read_text()
            self.assertGreater(
                len(content),
                100,
                f"Conversation file {file.name} should have substantial HTML content, "
                f"but got only {len(content)} characters."
            )

    def test_statistics_persistence_through_pipeline_stages(self):
        """Test that statistics persist correctly through all pipeline stages.
        
        This test will FAIL initially because statistics are lost between pipeline stages.
        """
        # Setup: Create Calls directory structure
        calls_dir = self.test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup: Create multiple test HTML files
        test_files = []
        for i in range(2):
            test_file = calls_dir / f"+123456789{i} - Text - 2023-01-01T12_0{i}_00Z.html"
            content = self.realistic_html_content.replace("+1234567890", f"+123456789{i}")
            test_file.write_text(content)
            test_files.append(test_file)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Stage 1: Process files
        file_mapping = {str(f): str(f) for f in test_files}
        stage1_stats = sms.process_html_files(file_mapping)
        
        # Stage 2: Check ConversationManager statistics
        stage2_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Stage 3: Finalize conversation files
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        stage3_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Stage 4: Generate index
        sms.CONVERSATION_MANAGER.generate_index_html(stage1_stats, 10.5)
        stage4_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Assert: Statistics should be consistent across all stages
        stages = [
            ("Stage 1: process_html_files()", stage1_stats),
            ("Stage 2: ConversationManager after processing", stage2_stats),
            ("Stage 3: ConversationManager after finalization", stage3_stats),
            ("Stage 4: ConversationManager after index generation", stage4_stats)
        ]
        
        base_stage_name, base_stats = stages[0]
        for stage_name, stage_stats in stages:
            self.assertEqual(
                base_stats['num_sms'],
                stage_stats['num_sms'],
                f"Statistics inconsistency: {base_stage_name} shows {base_stats['num_sms']} "
                f"SMS messages, but {stage_name} shows {stage_stats['num_sms']}. "
                "Statistics should be consistent across all pipeline stages."
            )

    def test_final_summary_statistics_accuracy(self):
        """Test that the final summary uses correct statistics.
        
        This test will FAIL initially because the final summary uses incorrect statistics.
        """
        # Setup: Create Calls directory structure
        calls_dir = self.test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup: Create test HTML file
        test_file = calls_dir / "test_conversation.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process the file
        file_mapping = {str(test_file): str(test_file)}
        process_stats = sms.process_html_files(file_mapping)
        
        # Action: Get ConversationManager statistics
        cm_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Action: Finalize and generate index (simulating the complete pipeline)
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        sms.CONVERSATION_MANAGER.generate_index_html(process_stats, 10.5)
        
        # Assert: Final summary should use ConversationManager statistics, not process_html_files() statistics
        self.assertEqual(
            process_stats['num_sms'],
            cm_stats['num_sms'],
            f"Final summary should use ConversationManager statistics ({cm_stats['num_sms']}) "
            f"not process_html_files() statistics ({process_stats['num_sms']}). "
            "This indicates the statistics synchronization is broken."
        )
        
        # Assert: Final statistics should be non-zero when messages are processed
        if cm_stats['num_sms'] > 0:
            self.assertGreater(
                process_stats['num_sms'],
                0,
                f"Final summary should show {cm_stats['num_sms']} SMS messages "
                f"when ConversationManager processed {cm_stats['num_sms']} messages."
            )

    def test_html_file_content_corresponds_to_statistics(self):
        """Test that HTML file content corresponds to the statistics.
        
        This test will FAIL initially because HTML files are empty despite statistics showing messages.
        """
        # Setup: Create Calls directory structure
        calls_dir = self.test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup: Create test HTML file
        test_file = calls_dir / "test_conversation.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process the file
        file_mapping = {str(test_file): str(test_file)}
        process_stats = sms.process_html_files(file_mapping)
        
        # Action: Finalize conversation files
        sms.CONVERSATION_MANAGER.finalize_conversation_files()
        
        # Get final statistics
        final_stats = sms.CONVERSATION_MANAGER.get_total_stats()
        
        # Check HTML files
        conversation_files = list(self.test_dir.glob("*.html"))
        conversation_files = [f for f in conversation_files if f.name != "index.html"]
        
        # Assert: HTML file count should correspond to statistics
        if final_stats['num_sms'] > 0:
            self.assertGreater(
                len(conversation_files),
                0,
                f"Should have created conversation HTML files when {final_stats['num_sms']} "
                "SMS messages were processed."
            )
            
            # Assert: HTML file content should correspond to statistics
            total_content_size = sum(f.stat().st_size for f in conversation_files)
            self.assertGreater(
                total_content_size,
                0,
                f"HTML files should have content when {final_stats['num_sms']} "
                "SMS messages were processed, but total content size is {total_content_size} bytes."
            )
            
            # Assert: HTML content should contain message text
            for file in conversation_files:
                content = file.read_text()
                self.assertIn(
                    "Hello, this is a test SMS message",
                    content,
                    f"HTML file {file.name} should contain the processed message text "
                    "when statistics show messages were processed."
                )
        else:
            # If statistics show 0, files should be empty or not created
            self.assertEqual(
                len(conversation_files),
                0,
                "Should not have created conversation HTML files when no messages were processed."
            )


if __name__ == '__main__':
    unittest.main()