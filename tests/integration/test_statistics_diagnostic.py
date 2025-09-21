"""
Diagnostic tests to identify exactly where statistics tracking fails.

These tests will FAIL initially and provide specific diagnostic information
about which methods are not updating statistics correctly.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sms
from core.conversation_manager import ConversationManager
from tests.base_test import BaseSMSTest


class TestStatisticsDiagnostic(BaseSMSTest):
    """Diagnostic tests to identify exactly where statistics tracking fails."""

    def setUp(self):
        super().setUp()
        # Create a mock phone lookup manager
        self.mock_phone_lookup = Mock()
        self.mock_phone_lookup.get_alias.return_value = "Test User"
        
        # Create a mock path manager
        self.mock_path_manager = Mock()

    def test_identify_missing_statistics_updates(self):
        """Identify which methods fail to update statistics.
        
        This test will FAIL and provide diagnostic information about:
        1. Which methods are called during message processing
        2. Which methods update statistics vs which don't
        3. The exact point where statistics tracking breaks
        """
        # Setup: Create conversation manager with diagnostic tracking
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        # Track initial state
        initial_conv_stats = dict(conversation_manager.conversation_stats)
        initial_total_stats = conversation_manager.get_total_stats()
        
        print(f"\n=== DIAGNOSTIC: Initial State ===")
        print(f"Initial conversation_stats: {initial_conv_stats}")
        print(f"Initial total_stats: {initial_total_stats}")
        
        # Action: Call write_message_with_content
        print(f"\n=== DIAGNOSTIC: Calling write_message_with_content ===")
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574400000,
            sender="Test User",
            message="Diagnostic test message"
        )
        
        # Check state after write_message_with_content
        after_write_conv_stats = dict(conversation_manager.conversation_stats)
        after_write_total_stats = conversation_manager.get_total_stats()
        
        print(f"After write_message_with_content:")
        print(f"  conversation_stats: {after_write_conv_stats}")
        print(f"  total_stats: {after_write_total_stats}")
        
        # Diagnostic assertions
        conv_stats_changed = after_write_conv_stats != initial_conv_stats
        total_stats_changed = after_write_total_stats != initial_total_stats
        
        print(f"\n=== DIAGNOSTIC: Change Detection ===")
        print(f"conversation_stats changed: {conv_stats_changed}")
        print(f"total_stats changed: {total_stats_changed}")
        
        if not conv_stats_changed:
            print("❌ DIAGNOSTIC: write_message_with_content() is NOT updating conversation_stats")
        else:
            print("✅ DIAGNOSTIC: write_message_with_content() IS updating conversation_stats")
        
        if not total_stats_changed:
            print("❌ DIAGNOSTIC: get_total_stats() is NOT reflecting changes from conversation_stats")
        else:
            print("✅ DIAGNOSTIC: get_total_stats() IS reflecting changes from conversation_stats")
        
        # Assert: At least one should change if the system is working
        self.assertTrue(
            conv_stats_changed or total_stats_changed,
            "Either conversation_stats or total_stats should change after writing a message. "
            "This diagnostic test shows that BOTH are failing to update, indicating "
            "write_message_with_content() is completely broken for statistics tracking."
        )

    def test_statistics_flow_tracing(self):
        """Trace the complete flow of statistics from message to final output.
        
        This test will FAIL and provide a complete trace of:
        1. Message processing flow
        2. Statistics update points
        3. Where statistics are lost or not updated
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        print(f"\n=== DIAGNOSTIC: Statistics Flow Tracing ===")
        
        # Step 1: Initial state
        step1_conv_stats = dict(conversation_manager.conversation_stats)
        step1_total_stats = conversation_manager.get_total_stats()
        print(f"Step 1 - Initial state:")
        print(f"  conversation_stats: {step1_conv_stats}")
        print(f"  total_stats: {step1_total_stats}")
        
        # Step 2: Open conversation file (should initialize stats)
        conversation_manager._open_conversation_file(conversation_id)
        step2_conv_stats = dict(conversation_manager.conversation_stats)
        step2_total_stats = conversation_manager.get_total_stats()
        print(f"\nStep 2 - After _open_conversation_file:")
        print(f"  conversation_stats: {step2_conv_stats}")
        print(f"  total_stats: {step2_total_stats}")
        
        # Check if conversation was initialized
        if conversation_id in step2_conv_stats:
            print(f"✅ DIAGNOSTIC: _open_conversation_file() initialized conversation_stats for '{conversation_id}'")
            conv_stats = step2_conv_stats[conversation_id]
            print(f"  Initial conversation stats: {conv_stats}")
        else:
            print(f"❌ DIAGNOSTIC: _open_conversation_file() did NOT initialize conversation_stats for '{conversation_id}'")
        
        # Step 3: Write message
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574400000,
            sender="Test User",
            message="Flow trace message"
        )
        step3_conv_stats = dict(conversation_manager.conversation_stats)
        step3_total_stats = conversation_manager.get_total_stats()
        print(f"\nStep 3 - After write_message_with_content:")
        print(f"  conversation_stats: {step3_conv_stats}")
        print(f"  total_stats: {step3_total_stats}")
        
        # Check if conversation stats were updated
        if conversation_id in step3_conv_stats:
            conv_stats = step3_conv_stats[conversation_id]
            sms_count = conv_stats.get('sms_count', 0)
            print(f"  conversation '{conversation_id}' sms_count: {sms_count}")
            
            if sms_count > 0:
                print(f"✅ DIAGNOSTIC: write_message_with_content() updated sms_count to {sms_count}")
            else:
                print(f"❌ DIAGNOSTIC: write_message_with_content() did NOT update sms_count (still {sms_count})")
        else:
            print(f"❌ DIAGNOSTIC: conversation '{conversation_id}' not found in conversation_stats")
        
        # Step 4: Check total stats aggregation
        total_sms = step3_total_stats.get('num_sms', 0)
        print(f"  total_stats num_sms: {total_sms}")
        
        if total_sms > 0:
            print(f"✅ DIAGNOSTIC: get_total_stats() aggregated to {total_sms}")
        else:
            print(f"❌ DIAGNOSTIC: get_total_stats() returned {total_sms} (aggregation failed)")
        
        # Step 5: Write another message to test accumulation
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574460000,
            sender="Test User",
            message="Second flow trace message"
        )
        step4_conv_stats = dict(conversation_manager.conversation_stats)
        step4_total_stats = conversation_manager.get_total_stats()
        print(f"\nStep 4 - After second write_message_with_content:")
        print(f"  conversation_stats: {step4_conv_stats}")
        print(f"  total_stats: {step4_total_stats}")
        
        # Check accumulation
        if conversation_id in step4_conv_stats:
            conv_stats = step4_conv_stats[conversation_id]
            sms_count = conv_stats.get('sms_count', 0)
            print(f"  conversation '{conversation_id}' sms_count: {sms_count}")
            
            if sms_count >= 2:
                print(f"✅ DIAGNOSTIC: Statistics are accumulating correctly ({sms_count})")
            else:
                print(f"❌ DIAGNOSTIC: Statistics are NOT accumulating correctly ({sms_count} < 2)")
        
        # Assert: Should have processed 2 messages
        final_total = step4_total_stats.get('num_sms', 0)
        self.assertGreaterEqual(
            final_total,
            2,
            f"Should have processed 2 messages, but total_stats shows {final_total}. "
            "This diagnostic trace shows exactly where statistics tracking fails."
        )

    def test_conversation_stats_structure_validation(self):
        """Validate the structure of conversation_stats and identify issues.
        
        This test will FAIL and provide detailed information about:
        1. The expected vs actual structure of conversation_stats
        2. Missing or incorrect fields
        3. Data type issues
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        conversation_id = "test_conversation"
        
        print(f"\n=== DIAGNOSTIC: Conversation Stats Structure Validation ===")
        
        # Expected structure based on code analysis
        expected_stats_structure = {
            'sms_count': int,
            'calls_count': int,
            'voicemails_count': int,
            'attachments_count': int,
            'latest_timestamp': int,
            'latest_message_time': str
        }
        
        print(f"Expected conversation_stats structure: {expected_stats_structure}")
        
        # Action: Open conversation file (should initialize stats)
        conversation_manager._open_conversation_file(conversation_id)
        
        # Check if conversation was created
        if conversation_id in conversation_manager.conversation_stats:
            actual_stats = conversation_manager.conversation_stats[conversation_id]
            print(f"Actual conversation_stats for '{conversation_id}': {actual_stats}")
            
            # Validate structure
            for expected_key, expected_type in expected_stats_structure.items():
                if expected_key in actual_stats:
                    actual_value = actual_stats[expected_key]
                    actual_type = type(actual_value)
                    
                    if isinstance(actual_value, expected_type):
                        print(f"✅ DIAGNOSTIC: '{expected_key}' has correct type {actual_type}")
                    else:
                        print(f"❌ DIAGNOSTIC: '{expected_key}' has wrong type {actual_type}, expected {expected_type}")
                else:
                    print(f"❌ DIAGNOSTIC: Missing key '{expected_key}' in conversation_stats")
            
            # Check initial values
            sms_count = actual_stats.get('sms_count', 'MISSING')
            print(f"Initial sms_count: {sms_count} (should be 0)")
            
            if sms_count == 0:
                print(f"✅ DIAGNOSTIC: sms_count correctly initialized to 0")
            else:
                print(f"❌ DIAGNOSTIC: sms_count incorrectly initialized to {sms_count}")
        
        else:
            print(f"❌ DIAGNOSTIC: Conversation '{conversation_id}' not found in conversation_stats")
            print(f"Available conversations: {list(conversation_manager.conversation_stats.keys())}")
        
        # Action: Write message and check structure again
        conversation_manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1672574400000,
            sender="Test User",
            message="Structure validation message"
        )
        
        if conversation_id in conversation_manager.conversation_stats:
            updated_stats = conversation_manager.conversation_stats[conversation_id]
            print(f"\nAfter write_message_with_content:")
            print(f"Updated conversation_stats: {updated_stats}")
            
            sms_count = updated_stats.get('sms_count', 'MISSING')
            print(f"Updated sms_count: {sms_count}")
            
            if sms_count == 1:
                print(f"✅ DIAGNOSTIC: sms_count correctly updated to 1")
            elif sms_count == 0:
                print(f"❌ DIAGNOSTIC: sms_count NOT updated (still 0) - this is the root cause!")
            else:
                print(f"❌ DIAGNOSTIC: sms_count has unexpected value {sms_count}")
        
        # Assert: Structure should be correct
        if conversation_id in conversation_manager.conversation_stats:
            stats = conversation_manager.conversation_stats[conversation_id]
            self.assertIn('sms_count', stats, "conversation_stats should contain 'sms_count' field")
            self.assertIsInstance(stats['sms_count'], int, "sms_count should be an integer")
            
            # The actual assertion that will fail
            self.assertGreater(
                stats['sms_count'],
                0,
                f"sms_count should be > 0 after writing a message, but got {stats['sms_count']}. "
                "This diagnostic test confirms that write_message_with_content() is not updating statistics."
            )

    def test_get_total_stats_aggregation_logic(self):
        """Test the aggregation logic in get_total_stats() method.
        
        This test will FAIL and provide diagnostic information about:
        1. How get_total_stats() aggregates conversation_stats
        2. Whether the key mapping is correct
        3. Whether the aggregation logic works
        """
        # Setup: Create conversation manager
        conversation_manager = ConversationManager(
            output_dir=self.test_dir
        )
        
        print(f"\n=== DIAGNOSTIC: get_total_stats() Aggregation Logic ===")
        
        # Manually set up conversation stats to test aggregation
        conversation_manager.conversation_stats = {
            'conv1': {
                'sms_count': 3,
                'calls_count': 1,
                'voicemails_count': 0,
                'attachments_count': 2,
                'latest_timestamp': 1672574400000,
                'latest_message_time': '2023-01-01 12:00:00'
            },
            'conv2': {
                'sms_count': 2,
                'calls_count': 0,
                'voicemails_count': 1,
                'attachments_count': 0,
                'latest_timestamp': 1672574460000,
                'latest_message_time': '2023-01-01 12:01:00'
            }
        }
        
        print(f"Manual conversation_stats setup:")
        for conv_id, stats in conversation_manager.conversation_stats.items():
            print(f"  {conv_id}: {stats}")
        
        # Expected totals
        expected_sms = 3 + 2  # 5
        expected_calls = 1 + 0  # 1
        expected_voicemails = 0 + 1  # 1
        
        print(f"\nExpected totals:")
        print(f"  SMS: {expected_sms}")
        print(f"  Calls: {expected_calls}")
        print(f"  Voicemails: {expected_voicemails}")
        
        # Action: Get total stats
        total_stats = conversation_manager.get_total_stats()
        print(f"\nActual total_stats: {total_stats}")
        
        # Diagnostic checks
        actual_sms = total_stats.get('num_sms', 'MISSING')
        actual_calls = total_stats.get('num_calls', 'MISSING')
        actual_voicemails = total_stats.get('num_voicemails', 'MISSING')
        
        print(f"\nAggregation results:")
        print(f"  num_sms: {actual_sms} (expected {expected_sms})")
        print(f"  num_calls: {actual_calls} (expected {expected_calls})")
        print(f"  num_voicemails: {actual_voicemails} (expected {expected_voicemails})")
        
        if actual_sms == expected_sms:
            print(f"✅ DIAGNOSTIC: SMS aggregation works correctly")
        else:
            print(f"❌ DIAGNOSTIC: SMS aggregation failed - got {actual_sms}, expected {expected_sms}")
        
        if actual_calls == expected_calls:
            print(f"✅ DIAGNOSTIC: Calls aggregation works correctly")
        else:
            print(f"❌ DIAGNOSTIC: Calls aggregation failed - got {actual_calls}, expected {expected_calls}")
        
        if actual_voicemails == expected_voicemails:
            print(f"✅ DIAGNOSTIC: Voicemails aggregation works correctly")
        else:
            print(f"❌ DIAGNOSTIC: Voicemails aggregation failed - got {actual_voicemails}, expected {expected_voicemails}")
        
        # Assert: Aggregation should work correctly
        self.assertEqual(
            actual_sms,
            expected_sms,
            f"get_total_stats() should aggregate SMS correctly: got {actual_sms}, expected {expected_sms}. "
            "This diagnostic test shows whether the aggregation logic is working."
        )


if __name__ == '__main__':
    unittest.main()
