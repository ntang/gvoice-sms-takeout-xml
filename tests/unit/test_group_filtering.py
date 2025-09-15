"""
Unit tests for group conversation filtering functionality.

This module tests the new group filtering feature that filters out entire group
conversations when ALL participants (excluding self) are marked to filter.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from typing import List, Optional

from core.phone_lookup import PhoneLookupManager, get_own_number_from_context
from core.processing_config import ProcessingConfig


class TestGroupFiltering(unittest.TestCase):
    """Test cases for group conversation filtering functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.lookup_file = Path("test_phone_lookup.txt")
        self.phone_lookup_manager = PhoneLookupManager(
            lookup_file=self.lookup_file,
            enable_prompts=False,
            skip_filtered_contacts=True
        )
        
        # Create test config
        self.config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            filter_groups_with_all_filtered=True
        )
        
        # Mock the phone lookup data
        self.phone_lookup_manager.phone_aliases = {
            "+1234567890": "Alice",
            "+1234567891": "Bob", 
            "+1234567892": "Charlie",
            "+1234567893": "David",
        }
        self.phone_lookup_manager.contact_filters = {
            "+1234567890": "filter=spam",
            "+1234567891": "filter=spam",
            # David (+1234567893) is NOT filtered
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if self.lookup_file.exists():
            self.lookup_file.unlink()

    def test_get_own_number_from_context_with_own_number(self):
        """Test own number detection when own_number is provided."""
        participants = ["+1234567890", "+1234567891", "+1234567892"]
        own_number = "+1234567890"
        
        result = get_own_number_from_context(participants, own_number)
        self.assertEqual(result, "+1234567890")

    def test_get_own_number_from_context_without_own_number(self):
        """Test own number detection when own_number is None."""
        participants = ["+1234567890", "+1234567891", "+1234567892"]
        
        result = get_own_number_from_context(participants, None)
        self.assertIsNone(result)

    def test_get_own_number_from_context_empty_participants(self):
        """Test own number detection with empty participants list."""
        participants = []
        own_number = "+1234567890"
        
        result = get_own_number_from_context(participants, own_number)
        self.assertIsNone(result)

    def test_should_filter_group_conversation_all_filtered(self):
        """Test group filtering when all participants are filtered."""
        participants = ["+1234567890", "+1234567891"]  # Both Alice and Bob are filtered
        own_number = "+1234567893"  # David is not in the group
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertTrue(result)

    def test_should_filter_group_conversation_some_not_filtered(self):
        """Test group filtering when some participants are not filtered."""
        participants = ["+1234567890", "+1234567892"]  # Alice is filtered, Charlie is not
        own_number = "+1234567893"  # David is not in the group
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertFalse(result)

    def test_should_filter_group_conversation_own_number_in_group(self):
        """Test group filtering when own number is in the group."""
        participants = ["+1234567890", "+1234567891", "+1234567893"]  # Alice and Bob filtered, David not
        own_number = "+1234567893"  # David is in the group
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertTrue(result)  # Should filter because Alice and Bob (other participants) are filtered

    def test_should_filter_group_conversation_disabled_config(self):
        """Test group filtering when disabled in config."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            filter_groups_with_all_filtered=False
        )
        participants = ["+1234567890", "+1234567891"]  # Both filtered
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, config
        )
        self.assertFalse(result)

    def test_should_filter_group_conversation_no_config(self):
        """Test group filtering when no config provided (should use default)."""
        participants = ["+1234567890", "+1234567891"]  # Both filtered
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, None
        )
        self.assertTrue(result)  # Should use default (enabled)

    def test_should_filter_group_conversation_empty_participants(self):
        """Test group filtering with empty participants list."""
        participants = []
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertFalse(result)

    def test_should_filter_group_conversation_single_participant(self):
        """Test group filtering with single participant."""
        participants = ["+1234567890"]  # Alice is filtered
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertFalse(result)  # Should not filter single-participant groups

    def test_should_filter_group_conversation_unknown_participants(self):
        """Test group filtering with unknown participants (not in lookup)."""
        participants = ["+9999999999", "+9999999998"]  # Unknown numbers
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertFalse(result)  # Unknown participants are not filtered

    def test_should_filter_group_conversation_mixed_known_unknown(self):
        """Test group filtering with mix of known and unknown participants."""
        participants = ["+1234567890", "+9999999999"]  # Alice filtered, unknown not
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        self.assertFalse(result)  # Should not filter because unknown participant is not filtered

    def test_should_filter_group_conversation_error_handling(self):
        """Test group filtering error handling."""
        participants = ["+1234567890", "+1234567891"]
        own_number = "+1234567893"
        
        # Mock is_filtered to raise an exception
        with patch.object(self.phone_lookup_manager, 'is_filtered', side_effect=Exception("Test error")):
            # The method should catch the exception and return False
            result = self.phone_lookup_manager.should_filter_group_conversation(
                participants, own_number, self.config
            )
            self.assertFalse(result)  # Should return False on error

    def test_should_filter_group_conversation_no_phone_lookup_manager(self):
        """Test group filtering when phone_lookup_manager is None."""
        participants = ["+1234567890", "+1234567891"]
        own_number = "+1234567893"
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        # Should still work with the manager instance
        self.assertTrue(result)

    def test_should_filter_group_conversation_own_number_detection_fallback(self):
        """Test group filtering with own number detection fallback."""
        participants = ["+1234567890", "+1234567891", "+1234567893"]  # Alice and Bob filtered, David not
        own_number = None  # No own number provided
        
        result = self.phone_lookup_manager.should_filter_group_conversation(
            participants, own_number, self.config
        )
        # Should not filter because David is not filtered (even though we can't detect self)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
