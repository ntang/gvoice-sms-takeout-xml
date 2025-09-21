"""
Statistics flow integration tests.

These tests will FAIL initially, exposing the critical issue where process_html_files()
returns hardcoded zero statistics instead of retrieving updated statistics from
ConversationManager.
"""

import os
import pytest
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sms
from tests.base_test import BaseSMSTest


class TestStatisticsFlowIntegration(BaseSMSTest):
    """Test that statistics flow correctly from ConversationManager to process_html_files()."""

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
        </body>
        </html>
        """

    def test_process_html_files_returns_updated_statistics(self):
        """Test that process_html_files() returns statistics from ConversationManager.
        
        This test will FAIL initially because process_html_files() returns zeros
        instead of retrieving updated statistics from ConversationManager.
        """
        # Setup: Create Calls directory structure
        calls_dir = self.test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup: Create test HTML file in the Calls directory
        test_file = calls_dir / "+1234567890 - Text - 2023-01-01T12_00_00Z.html"
        test_file.write_text(self.realistic_html_content)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Call process_html_files() with file mapping
        file_mapping = {str(test_file): str(test_file)}
        returned_stats = sms.process_html_files(file_mapping)
        
        # Action: Get statistics directly from ConversationManager
        conversation_manager = sms.CONVERSATION_MANAGER
        cm_stats = conversation_manager.get_total_stats()
        
        # Assert: process_html_files() should return the same statistics as ConversationManager
        self.assertEqual(
            returned_stats['num_sms'],
            cm_stats['num_sms'],
            f"process_html_files() returned {returned_stats['num_sms']} SMS messages, "
            f"but ConversationManager shows {cm_stats['num_sms']}. "
            "This indicates process_html_files() is not retrieving updated statistics from ConversationManager."
        )
        
        # Assert: Both should be non-zero if messages were processed
        if cm_stats['num_sms'] > 0:
            self.assertGreater(
                returned_stats['num_sms'],
                0,
                f"process_html_files() should return non-zero statistics ({cm_stats['num_sms']}) "
                f"when ConversationManager shows {cm_stats['num_sms']} messages processed."
            )
        
        # Assert: All statistics should match
        for stat_key in ['num_sms', 'num_calls', 'num_voicemails', 'num_img', 'num_vcf']:
            self.assertEqual(
                returned_stats[stat_key],
                cm_stats[stat_key],
                f"process_html_files() and ConversationManager disagree on {stat_key}: "
                f"returned {returned_stats[stat_key]} vs CM {cm_stats[stat_key]}"
            )

    def test_end_to_end_statistics_synchronization(self):
        """Test that statistics flow correctly from processing to final summary.
        
        This test will FAIL initially because final summary uses wrong statistics source.
        """
        # Setup: Create Calls directory structure
        calls_dir = self.test_dir / "Calls"
        calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup: Create multiple test HTML files
        test_files = []
        for i in range(3):
            test_file = calls_dir / f"+123456789{i} - Text - 2023-01-01T12_0{i}_00Z.html"
            content = self.realistic_html_content.replace("+1234567890", f"+123456789{i}")
            test_file.write_text(content)
            test_files.append(test_file)
        
        # Setup: Initialize processing
        sms.setup_processing_paths(self.test_dir, False, False, None)
        
        # Action: Process all files
        file_mapping = {str(f): str(f) for f in test_files}
        returned_stats = sms.process_html_files(file_mapping)
        
        # Action: Get final statistics from ConversationManager
        conversation_manager = sms.CONVERSATION_MANAGER
        final_cm_stats = conversation_manager.get_total_stats()
        
        # Action: Finalize conversation files
        conversation_manager.finalize_conversation_files()
        
        # Get statistics after finalization
        post_finalization_stats = conversation_manager.get_total_stats()
        
        # Assert: Statistics should be consistent throughout the pipeline
        self.assertEqual(
            returned_stats['num_sms'],
            final_cm_stats['num_sms'],
            "Statistics from process_html_files() should match ConversationManager statistics"
        )
        
        self.assertEqual(
            final_cm_stats['num_sms'],
            post_finalization_stats['num_sms'],
            "Statistics should not change during finalization"
        )
        
        # Assert: Should have processed messages from all files
        expected_min_messages = len(test_files) * 3  # 3 messages per file
        self.assertGreaterEqual(
            returned_stats['num_sms'],
            expected_min_messages,
            f"Should have processed at least {expected_min_messages} messages "
            f"(3 files × 3 messages each), but got {returned_stats['num_sms']}"
        )

    def test_statistics_source_consistency(self):
        """Test that all statistics sources return the same values.
        
        This test will FAIL initially because different parts of system use different statistics.
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
        
        # Action: Get statistics from multiple sources
        conversation_manager = sms.CONVERSATION_MANAGER
        cm_stats = conversation_manager.get_total_stats()
        conversation_stats = conversation_manager.conversation_stats
        
        # Calculate expected statistics from conversation_stats
        expected_sms = sum(stats.get('sms_count', 0) for stats in conversation_stats.values())
        expected_calls = sum(stats.get('calls_count', 0) for stats in conversation_stats.values())
        expected_voicemails = sum(stats.get('voicemails_count', 0) for stats in conversation_stats.values())
        
        # Assert: All statistics sources should be consistent
        statistics_sources = [
            ("process_html_files()", process_stats),
            ("ConversationManager.get_total_stats()", cm_stats),
            ("conversation_stats aggregation", {
                'num_sms': expected_sms,
                'num_calls': expected_calls,
                'num_voicemails': expected_voicemails
            })
        ]
        
        # Compare all sources
        base_source_name, base_stats = statistics_sources[0]
        for source_name, source_stats in statistics_sources[1:]:
            for stat_key in ['num_sms', 'num_calls', 'num_voicemails']:
                self.assertEqual(
                    base_stats[stat_key],
                    source_stats[stat_key],
                    f"Statistics inconsistency: {base_source_name} shows {base_stats[stat_key]} "
                    f"for {stat_key}, but {source_name} shows {source_stats[stat_key]}. "
                    "This indicates different parts of the system are using different statistics sources."
                )

    @pytest.mark.skip(reason="Statistics tracking architecture needs review")
    def test_statistics_disconnect_detection(self):
        """Test that we can detect when statistics disconnect occurs.
        
        This test will FAIL initially because the disconnect exists and is not detected.
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
        conversation_manager = sms.CONVERSATION_MANAGER
        cm_stats = conversation_manager.get_total_stats()
        
        # Detect statistics disconnect
        disconnect_detected = (
            cm_stats['num_sms'] > 0 and process_stats['num_sms'] == 0
        ) or (
            cm_stats['num_sms'] != process_stats['num_sms']
        )
        
        # Assert: Statistics disconnect should be detected
        self.assertTrue(
            disconnect_detected,
            f"Statistics disconnect should be detected: ConversationManager shows "
            f"{cm_stats['num_sms']} SMS messages, but process_html_files() returned "
            f"{process_stats['num_sms']}. This disconnect needs to be fixed."
        )
        
        # Assert: If disconnect is detected, it should be logged or handled
        if disconnect_detected:
            # This assertion will help us verify that the fix properly handles the disconnect
            self.assertGreater(
                cm_stats['num_sms'],
                0,
                "ConversationManager should have processed messages when disconnect is detected"
            )


if __name__ == '__main__':
    unittest.main()

