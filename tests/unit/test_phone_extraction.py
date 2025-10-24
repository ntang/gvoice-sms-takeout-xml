"""
Unit tests for phone number extraction from SMS messages.

Tests the fix for extracting phone numbers from files containing only outgoing messages,
ensuring the user's own number is skipped and the recipient's number is correctly identified.
"""

import pytest
from bs4 import BeautifulSoup
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import the functions we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sms import get_first_phone_number, create_dummy_participant


class TestPhoneNumberExtraction:
    """Test phone number extraction with own_number filtering."""

    def test_extract_from_mixed_messages(self):
        """Test extraction from file with both incoming and outgoing messages."""
        # Create HTML with both user's number and recipient's number
        html = """
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+12034173178">
                    <span class="fn">Ed Harbur</span>
                </a>
            </cite>
            <q>Message from Ed</q>
        </div>
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>
            <q>Message from Me</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # Extract without own_number - should return first number found (Ed's)
        phone_number, participant = get_first_phone_number(messages, 0, own_number=None)
        assert phone_number == "+12034173178"  # E164 format
        
        # Extract with own_number - should skip user's number and return Ed's
        phone_number, participant = get_first_phone_number(
            messages, 0, own_number="+13474106066"
        )
        assert phone_number == "+12034173178"  # E164 format

    def test_extract_from_outgoing_only_messages(self):
        """Test extraction from file with ONLY outgoing messages (the bug scenario)."""
        # Create HTML with only user's messages (like Ed Harbur - Text - 2024-12-05T23_40_41Z.html)
        html = """
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>
            <q>Apologies for taking so long to get back to you.</q>
        </div>
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>
            <q>And just to confirm, what we discussed...</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # WITHOUT own_number parameter - returns user's number (OLD BUGGY BEHAVIOR)
        phone_number, participant = get_first_phone_number(messages, 0, own_number=None)
        assert phone_number == "+13474106066"  # E164 format
        
        # WITH own_number parameter - should skip user's number and use fallback
        # In this case, no other number exists in messages, so it returns 0 (fallback will be used)
        phone_number, participant = get_first_phone_number(
            messages, 0, own_number="+13474106066"
        )
        # Should return 0 since all numbers in messages are the user's own number
        assert phone_number == 0

    def test_extract_with_fallback_number(self):
        """Test that fallback number is used when no valid participant number found."""
        # Empty messages
        messages = []
        
        # Fallback number should be returned
        phone_number, participant = get_first_phone_number(
            messages, "+12034173178", own_number="+13474106066"
        )
        assert phone_number == "+12034173178"  # E164 format

    def test_skip_own_number_in_tel_links(self):
        """Test that own_number is skipped when found in tel: links (Strategy 2)."""
        html = """
        <div class="message">
            <a href="tel:+13474106066">Me</a>
            <q>My message</q>
        </div>
        <div class="message">
            <a href="tel:+12034173178">Ed Harbur</a>
            <q>Ed's message</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # Should skip user's number and return Ed's number
        phone_number, participant = get_first_phone_number(
            messages, 0, own_number="+13474106066"
        )
        assert phone_number == "+12034173178"  # E164 format

    def test_skip_own_number_in_text_content(self):
        """Test that own_number is skipped when found in text content (Strategy 3)."""
        html = """
        <div class="message">
            <q>Call me at +13474106066</q>
        </div>
        <div class="message">
            <q>Or call +12034173178</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # Should skip user's number and return the other number
        phone_number, participant = get_first_phone_number(
            messages, 0, own_number="+13474106066"
        )
        assert phone_number == "+12034173178"  # E164 format

    def test_extract_without_own_number_param(self):
        """Test backward compatibility - function works without own_number parameter."""
        html = """
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+12034173178">
                    <span class="fn">Ed Harbur</span>
                </a>
            </cite>
            <q>Test message</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # Should work without own_number parameter (defaults to None)
        phone_number, participant = get_first_phone_number(messages, 0)
        assert phone_number == "+12034173178"  # E164 format

    def test_real_world_scenario_ed_harbur(self):
        """
        Test the exact scenario from the bug report.
        
        File: Ed Harbur - Text - 2024-12-05T23_40_41Z.html
        Contains only messages from user (Me) to Ed Harbur.
        Should NOT return user's number; should use fallback mechanism.
        """
        # Exact HTML structure from the problematic file
        html = """
        <div class="message">
            <abbr class="dt" title="2024-12-05T18:40:41.580-05:00">Dec 5, 2024, 6:40:41 PM</abbr>:
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>:
            <q>Apologies for taking so long to get back to you. We'll take the wet bar.</q>
        </div>
        <div class="message">
            <abbr class="dt" title="2024-12-05T18:45:16.883-05:00">Dec 5, 2024, 6:45:16 PM</abbr>:
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>:
            <q>And just to confirm, what we discussed...</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        user_number = "+13474106066"  # E164 format
        ed_number = "+12034173178"  # E164 format - Would come from filename or other file
        
        # Extract with own_number - should NOT return user's number
        phone_number, participant = get_first_phone_number(
            messages, ed_number, own_number=user_number
        )
        
        # Should return the fallback number (Ed's) since all messages are from user
        assert phone_number == ed_number
        assert phone_number != user_number


class TestCreateDummyParticipant:
    """Test the dummy participant creation helper."""

    def test_create_dummy_participant(self):
        """Test creating a dummy participant."""
        phone_number = "+1 203-417-3178"
        participant = create_dummy_participant(phone_number)
        
        assert participant is not None
        assert "tel:" in str(participant)
        assert phone_number in str(participant)

    def test_create_dummy_participant_with_int(self):
        """Test creating a dummy participant with integer phone number."""
        phone_number = 2034173178
        participant = create_dummy_participant(phone_number)
        
        assert participant is not None
        assert str(phone_number) in str(participant)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

