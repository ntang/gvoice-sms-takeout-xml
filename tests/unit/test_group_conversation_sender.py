"""
Unit tests for group conversation sender detection functionality.

This module tests the enhanced sender detection for group conversations
without affecting existing individual conversation functionality.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import os
import sys
from pathlib import Path

# Add project root to sys.path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sms import get_enhanced_sender_for_group


class TestGroupConversationSender(unittest.TestCase):
    """Test cases for enhanced sender detection in group conversations."""

    def setUp(self):
        """Set up test fixtures."""
        self.group_participants = ["+13475677474", "+15516890187", "+13474106066"]

    def test_me_message_detection(self):
        """Test detection of 'Me' messages in group conversations."""
        # Create a mock message with "Me" pattern: <abbr class="fn" title="">Me</abbr>
        mock_message = Mock()
        mock_cite = Mock()
        mock_abbr = Mock()
        
        # Mock the "Me" message structure
        mock_abbr.get_text.return_value = "Me"
        mock_cite.find.return_value = mock_abbr
        mock_cite.find_all.return_value = []
        mock_message.cite = mock_cite
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "Me")

    def test_other_participant_message_detection(self):
        """Test detection of other participant messages in group conversations."""
        # Create a mock message with other participant pattern: <span class="fn">Name</span>
        mock_message = Mock()
        mock_cite = Mock()
        mock_span = Mock()
        mock_tel_link = Mock()
        
        # Mock the other participant message structure
        mock_span.get_text.return_value = "Maria Teresa De la Rosa"
        mock_tel_link.get.return_value = "tel:+15516890187"
        mock_cite.find.side_effect = lambda tag, **kwargs: {
            ("span",): mock_span,
            ("a",): mock_tel_link
        }.get((tag,))
        mock_cite.find_all.return_value = []
        mock_message.cite = mock_cite
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "+15516890187")

    def test_phone_number_extraction_from_tel_link(self):
        """Test extraction of phone numbers from tel: links."""
        # Create a mock message with tel: link
        mock_message = Mock()
        mock_cite = Mock()
        mock_tel_link = Mock()
        
        # Mock the tel: link structure
        mock_tel_link.get.return_value = "tel:+13475677474"
        mock_cite.find.return_value = None  # No span or abbr
        mock_cite.find_all.return_value = [mock_tel_link]
        mock_message.cite = mock_cite
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "+13475677474")

    def test_fallback_to_me_when_no_cite(self):
        """Test fallback to 'Me' when no cite element is found."""
        mock_message = Mock()
        mock_message.cite = None
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "Me")

    def test_fallback_to_me_when_phone_not_in_participants(self):
        """Test fallback to 'Me' when phone number is not in group participants."""
        # Create a mock message with phone number not in group
        mock_message = Mock()
        mock_cite = Mock()
        mock_span = Mock()
        mock_tel_link = Mock()
        
        # Mock message with phone number not in group
        mock_span.get_text.return_value = "Unknown Person"
        mock_tel_link.get.return_value = "tel:+19999999999"
        mock_cite.find.side_effect = lambda tag, **kwargs: {
            ("span",): mock_span,
            ("a",): mock_tel_link
        }.get((tag,))
        mock_cite.find_all.return_value = []
        mock_message.cite = mock_cite
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "Me")

    def test_exception_handling(self):
        """Test that exceptions are handled gracefully and fallback to 'Me'."""
        mock_message = Mock()
        mock_cite = Mock()
        
        # Make the cite element raise an exception
        mock_cite.find.side_effect = Exception("Test exception")
        mock_message.cite = mock_cite
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "Me")

    def test_real_google_voice_html_structure(self):
        """Test with actual Google Voice HTML structure patterns."""
        from bs4 import BeautifulSoup
        
        # Test "Me" message HTML structure
        me_html = '''
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>
            <q>Hello everyone!</q>
        </div>
        '''
        me_soup = BeautifulSoup(me_html, 'html.parser')
        me_message = me_soup.find('div', class_='message')
        
        result = get_enhanced_sender_for_group(me_message, self.group_participants)
        self.assertEqual(result, "Me")
        
        # Test other participant message HTML structure
        other_html = '''
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+15516890187">
                    <span class="fn">Maria Teresa De la Rosa</span>
                </a>
            </cite>
            <q>Hi there!</q>
        </div>
        '''
        other_soup = BeautifulSoup(other_html, 'html.parser')
        other_message = other_soup.find('div', class_='message')
        
        result = get_enhanced_sender_for_group(other_message, self.group_participants)
        self.assertEqual(result, "+15516890187")

    def test_multiple_tel_links(self):
        """Test handling of messages with multiple tel: links."""
        mock_message = Mock()
        mock_cite = Mock()
        mock_tel_link1 = Mock()
        mock_tel_link2 = Mock()
        
        # Mock multiple tel: links
        mock_tel_link1.get.return_value = "tel:+19999999999"  # Not in group
        mock_tel_link2.get.return_value = "tel:+13475677474"  # In group
        mock_cite.find.return_value = None  # No span or abbr
        mock_cite.find_all.return_value = [mock_tel_link1, mock_tel_link2]
        mock_message.cite = mock_cite
        
        result = get_enhanced_sender_for_group(mock_message, self.group_participants)
        self.assertEqual(result, "+13475677474")

    def test_empty_group_participants(self):
        """Test behavior with empty group participants list."""
        mock_message = Mock()
        mock_cite = Mock()
        mock_span = Mock()
        mock_tel_link = Mock()
        
        # Mock message structure
        mock_span.get_text.return_value = "Test Person"
        mock_tel_link.get.return_value = "tel:+15516890187"
        mock_cite.find.side_effect = lambda tag, **kwargs: {
            ("span",): mock_span,
            ("a",): mock_tel_link
        }.get((tag,))
        mock_cite.find_all.return_value = []
        mock_message.cite = mock_cite
        
        # Test with empty participants list
        result = get_enhanced_sender_for_group(mock_message, [])
        self.assertEqual(result, "Me")


if __name__ == '__main__':
    unittest.main()
