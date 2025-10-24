"""
Unit tests for commercial conversation filter.

This module tests the commercial/spam conversation detection logic that identifies
conversations consisting primarily of commercial messages followed by unsubscribe
responses (e.g., "STOP").

Test Coverage:
- Basic unsubscribe patterns (STOP, UNSUBSCRIBE, etc.)
- Confirmation message detection
- Edge cases (whitespace, case sensitivity, multiple stops)
- False positives (real conversations with STOP word)
- Message structure validation

Author: Claude Code
Date: 2025-10-21
"""

import pytest
from core.commercial_filter import (
    is_unsubscribe_word,
    is_confirmation_message,
    is_commercial_conversation,
    UNSUBSCRIBE_WORDS,
    CONFIRMATION_PATTERNS,
)


class TestUnsubscribeWordDetection:
    """Test detection of unsubscribe keywords in messages."""

    def test_simple_stop_word(self):
        """Test basic STOP word detection."""
        assert is_unsubscribe_word("STOP") is True
        assert is_unsubscribe_word("stop") is True
        assert is_unsubscribe_word("Stop") is True

    def test_stop_with_whitespace(self):
        """Test STOP word with surrounding whitespace."""
        assert is_unsubscribe_word("  STOP  ") is True
        assert is_unsubscribe_word("\tSTOP\n") is True
        assert is_unsubscribe_word(" stop ") is True

    def test_various_unsubscribe_words(self):
        """Test different unsubscribe keywords."""
        unsubscribe_words = [
            "STOP",
            "UNSUBSCRIBE",
            "CANCEL",
            "REMOVE",
            "OPT-OUT",
            "OPTOUT",
            "STOP ALL",
            "END",
            "QUIT",
        ]
        for word in unsubscribe_words:
            assert is_unsubscribe_word(word) is True, f"Failed for: {word}"
            assert is_unsubscribe_word(word.lower()) is True, f"Failed for: {word.lower()}"

    def test_stop_in_sentence_is_not_unsubscribe(self):
        """Test that STOP as part of a sentence is not detected."""
        assert is_unsubscribe_word("Please stop texting me") is False
        assert is_unsubscribe_word("I want to stop") is False
        assert is_unsubscribe_word("Can you stop calling?") is False
        assert is_unsubscribe_word("Stop by my house") is False

    def test_empty_or_whitespace_only(self):
        """Test empty strings or whitespace-only strings."""
        assert is_unsubscribe_word("") is False
        assert is_unsubscribe_word("   ") is False
        assert is_unsubscribe_word("\t\n") is False

    def test_non_unsubscribe_words(self):
        """Test that regular words are not detected as unsubscribe words."""
        assert is_unsubscribe_word("Hello") is False
        assert is_unsubscribe_word("Thanks") is False
        assert is_unsubscribe_word("OK") is False
        assert is_unsubscribe_word("Yes") is False


class TestConfirmationMessageDetection:
    """Test detection of unsubscribe confirmation messages."""

    def test_simple_confirmation_messages(self):
        """Test basic confirmation message patterns."""
        confirmations = [
            "You have been unsubscribed",
            "You've been removed from our list",
            "You will no longer receive messages",
            "Successfully opted out",
            "Unsubscribe successful",
        ]
        for msg in confirmations:
            assert is_confirmation_message(msg) is True, f"Failed for: {msg}"

    def test_case_insensitive_confirmation(self):
        """Test confirmation detection is case-insensitive."""
        assert is_confirmation_message("YOU HAVE BEEN UNSUBSCRIBED") is True
        assert is_confirmation_message("you have been unsubscribed") is True
        assert is_confirmation_message("You Have Been Unsubscribed") is True

    def test_confirmation_with_extra_text(self):
        """Test confirmation messages with surrounding text."""
        assert is_confirmation_message(
            "Thank you! You have been unsubscribed from our marketing list."
        ) is True
        assert is_confirmation_message(
            "OK, you will no longer receive SMS from us. Reply HELP for assistance."
        ) is True

    def test_non_confirmation_messages(self):
        """Test that regular messages are not detected as confirmations."""
        assert is_confirmation_message("Hello, how are you?") is False
        assert is_confirmation_message("Thanks for your message") is False
        assert is_confirmation_message("OK") is False
        assert is_confirmation_message("Got it") is False

    def test_empty_message(self):
        """Test empty or whitespace-only messages."""
        assert is_confirmation_message("") is False
        assert is_confirmation_message("   ") is False


class TestCommercialConversationDetection:
    """Test detection of commercial/spam conversations."""

    def test_simple_stop_pattern(self):
        """Test basic commercial pattern: spam -> STOP -> confirmation."""
        messages = [
            {
                "timestamp": 1000,
                "sender": "+15551234567",
                "text": "Get 50% off! Reply STOP to unsubscribe",
            },
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
            {
                "timestamp": 3000,
                "sender": "+15551234567",
                "text": "You have been unsubscribed",
            },
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_stop_with_no_confirmation(self):
        """Test commercial pattern: spam -> STOP (no confirmation)."""
        messages = [
            {
                "timestamp": 1000,
                "sender": "+15551234567",
                "text": "Flash sale! Text STOP to opt out",
            },
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_multiple_spam_messages_before_stop(self):
        """Test commercial pattern with multiple spam messages before STOP."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Sale alert!"},
            {
                "timestamp": 2000,
                "sender": "+15551234567",
                "text": "Don't miss out! 24 hours only!",
            },
            {
                "timestamp": 3000,
                "sender": "+15551234567",
                "text": "Last chance! Reply STOP to unsubscribe",
            },
            {"timestamp": 4000, "sender": "Me", "text": "STOP"},
            {
                "timestamp": 5000,
                "sender": "+15551234567",
                "text": "You've been removed",
            },
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_case_insensitive_stop(self):
        """Test that STOP detection is case-insensitive."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Buy now!"},
            {"timestamp": 2000, "sender": "Me", "text": "stop"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_stop_with_whitespace(self):
        """Test STOP with surrounding whitespace."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Special offer!"},
            {"timestamp": 2000, "sender": "Me", "text": "  STOP  "},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_various_unsubscribe_words(self):
        """Test different unsubscribe words (UNSUBSCRIBE, CANCEL, etc.)."""
        for word in ["UNSUBSCRIBE", "CANCEL", "REMOVE", "OPT-OUT", "QUIT"]:
            messages = [
                {"timestamp": 1000, "sender": "+15551234567", "text": "Promotion!"},
                {"timestamp": 2000, "sender": "Me", "text": word},
            ]
            assert (
                is_commercial_conversation(messages, my_identifier="Me") is True
            ), f"Failed for word: {word}"

    def test_stop_not_alone_is_not_commercial(self):
        """Test that STOP in a real conversation is not detected as commercial."""
        messages = [
            {"timestamp": 1000, "sender": "Alice", "text": "Are you coming over?"},
            {"timestamp": 2000, "sender": "Me", "text": "Please stop calling me"},
            {"timestamp": 3000, "sender": "Alice", "text": "Sorry, won't happen again"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_real_conversation_after_spam_is_not_commercial(self):
        """Test that real conversation after unsubscribe is not commercial."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Sale today!"},
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
            {
                "timestamp": 3000,
                "sender": "+15551234567",
                "text": "You have been unsubscribed",
            },
            {"timestamp": 4000, "sender": "+15551234567", "text": "Hey, is this John?"},
            {"timestamp": 5000, "sender": "Me", "text": "Yes, who's this?"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_real_conversation_before_spam_is_not_commercial(self):
        """Test that real conversation before spam makes it not commercial."""
        messages = [
            {"timestamp": 1000, "sender": "Alice", "text": "Hey, how are you?"},
            {"timestamp": 2000, "sender": "Me", "text": "Good, you?"},
            {"timestamp": 3000, "sender": "Alice", "text": "Great! Sale alert!"},
            {"timestamp": 4000, "sender": "Me", "text": "STOP"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_no_stop_is_not_commercial(self):
        """Test that spam without STOP response is not detected as commercial."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Flash sale!"},
            {
                "timestamp": 2000,
                "sender": "+15551234567",
                "text": "Don't miss out! Reply STOP to unsubscribe",
            },
        ]
        # No STOP response from user
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_empty_conversation(self):
        """Test empty conversation list."""
        messages = []
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_single_message_is_not_commercial(self):
        """Test single message is not commercial."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Flash sale!"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_only_my_messages_is_not_commercial(self):
        """Test conversation with only my messages is not commercial."""
        messages = [
            {"timestamp": 1000, "sender": "Me", "text": "Hello?"},
            {"timestamp": 2000, "sender": "Me", "text": "Anyone there?"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_stop_as_first_message_is_not_commercial(self):
        """Test STOP as first message (no prior spam) is not commercial."""
        messages = [
            {"timestamp": 1000, "sender": "Me", "text": "STOP"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_multiple_conversations_mixed(self):
        """Test conversation with real dialogue mixed with spam."""
        messages = [
            {"timestamp": 1000, "sender": "Bob", "text": "Want to grab lunch?"},
            {"timestamp": 2000, "sender": "Me", "text": "Sure, when?"},
            {"timestamp": 3000, "sender": "Bob", "text": "How about noon?"},
            {"timestamp": 4000, "sender": "Me", "text": "Perfect"},
            # Later: spam appears
            {"timestamp": 5000, "sender": "Bob", "text": "SPAM: Flash sale!"},
            {"timestamp": 6000, "sender": "Me", "text": "STOP"},
        ]
        # This should NOT be commercial because there's real conversation before spam
        assert is_commercial_conversation(messages, my_identifier="Me") is False

    def test_confirmation_only_after_stop(self):
        """Test that only confirmation messages appear after STOP."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Sale alert!"},
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
            {
                "timestamp": 3000,
                "sender": "+15551234567",
                "text": "You have been unsubscribed",
            },
            {
                "timestamp": 4000,
                "sender": "+15551234567",
                "text": "You will no longer receive messages",
            },
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_non_confirmation_after_stop_is_not_commercial(self):
        """Test that non-confirmation messages after STOP make it not commercial."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Sale alert!"},
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
            {
                "timestamp": 3000,
                "sender": "+15551234567",
                "text": "Why do you want to unsubscribe?",
            },
        ]
        # Non-confirmation response suggests real conversation
        assert is_commercial_conversation(messages, my_identifier="Me") is False


class TestMessageDataStructure:
    """Test that the filter handles various message data structures correctly."""

    def test_messages_with_attachments(self):
        """Test messages with attachments field."""
        messages = [
            {
                "timestamp": 1000,
                "sender": "+15551234567",
                "text": "Check out this deal!",
                "attachments": [],
            },
            {"timestamp": 2000, "sender": "Me", "text": "STOP", "attachments": []},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_messages_with_formatted_time(self):
        """Test messages with formatted_time field."""
        messages = [
            {
                "timestamp": 1000,
                "sender": "+15551234567",
                "text": "Limited offer!",
                "formatted_time": "2024-10-21 10:00:00",
            },
            {
                "timestamp": 2000,
                "sender": "Me",
                "text": "STOP",
                "formatted_time": "2024-10-21 10:05:00",
            },
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_messages_missing_optional_fields(self):
        """Test messages with only required fields (timestamp, sender, text)."""
        messages = [
            {"timestamp": 1000, "sender": "+15551234567", "text": "Sale!"},
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_conversation(self):
        """Test commercial detection in a very long spam conversation."""
        messages = []
        # 20 spam messages
        for i in range(20):
            messages.append(
                {
                    "timestamp": 1000 + i * 1000,
                    "sender": "+15551234567",
                    "text": f"Spam message {i}",
                }
            )
        # User responds with STOP
        messages.append({"timestamp": 21000, "sender": "Me", "text": "STOP"})
        # Confirmation
        messages.append(
            {
                "timestamp": 22000,
                "sender": "+15551234567",
                "text": "You have been unsubscribed",
            }
        )
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_unicode_in_messages(self):
        """Test messages with Unicode characters."""
        messages = [
            {
                "timestamp": 1000,
                "sender": "+15551234567",
                "text": "🎉 Flash Sale! 50% off! 🎉",
            },
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
        ]
        assert is_commercial_conversation(messages, my_identifier="Me") is True

    def test_different_my_identifiers(self):
        """Test with different user identifier formats."""
        # Test with phone number
        messages = [
            {"timestamp": 1000, "sender": "+15559999999", "text": "Sale!"},
            {"timestamp": 2000, "sender": "+15551111111", "text": "STOP"},
        ]
        assert (
            is_commercial_conversation(messages, my_identifier="+15551111111") is True
        )

        # Test with alias
        messages = [
            {"timestamp": 1000, "sender": "SpamBot", "text": "Sale!"},
            {"timestamp": 2000, "sender": "John", "text": "STOP"},
        ]
        assert is_commercial_conversation(messages, my_identifier="John") is True

    def test_messages_out_of_order(self):
        """Test that filter works even if messages are not sorted by timestamp."""
        messages = [
            {"timestamp": 3000, "sender": "+15551234567", "text": "Unsubscribed"},
            {"timestamp": 1000, "sender": "+15551234567", "text": "Sale!"},
            {"timestamp": 2000, "sender": "Me", "text": "STOP"},
        ]
        # Filter should sort by timestamp internally
        assert is_commercial_conversation(messages, my_identifier="Me") is True


class TestUnsubscribeWordsConstant:
    """Test the UNSUBSCRIBE_WORDS constant is properly defined."""

    def test_unsubscribe_words_exists(self):
        """Test that UNSUBSCRIBE_WORDS is defined and is a set."""
        assert UNSUBSCRIBE_WORDS is not None
        assert isinstance(UNSUBSCRIBE_WORDS, set)

    def test_unsubscribe_words_contains_common_words(self):
        """Test that common unsubscribe words are included."""
        required_words = {"stop", "unsubscribe", "cancel", "remove"}
        assert required_words.issubset(UNSUBSCRIBE_WORDS)


class TestConfirmationPatternsConstant:
    """Test the CONFIRMATION_PATTERNS constant is properly defined."""

    def test_confirmation_patterns_exists(self):
        """Test that CONFIRMATION_PATTERNS is defined and is a list."""
        assert CONFIRMATION_PATTERNS is not None
        assert isinstance(CONFIRMATION_PATTERNS, list)

    def test_confirmation_patterns_are_strings(self):
        """Test that all confirmation patterns are strings."""
        for pattern in CONFIRMATION_PATTERNS:
            assert isinstance(pattern, str)

    def test_confirmation_patterns_contains_common_patterns(self):
        """Test that common confirmation patterns are included."""
        patterns_lower = [p.lower() for p in CONFIRMATION_PATTERNS]
        # At least one pattern should match "unsubscribe"
        assert any("unsubscrib" in p for p in patterns_lower)
