"""
Commercial Conversation Filter

This module provides logic to detect and filter commercial/spam conversations
based on unsubscribe patterns. A conversation is considered commercial if it
consists primarily of:

1. One or more messages from a sender (commercial/spam content)
2. A response from the user containing ONLY an unsubscribe word (STOP, UNSUBSCRIBE, etc.)
3. Either no further messages OR only confirmation messages acknowledging unsubscription
4. No real conversation before or after the unsubscribe interaction

This follows a post-processing approach: conversations are analyzed after all
messages have been collected, allowing for accurate pattern detection with full
conversation context.

Author: Claude Code
Date: 2025-10-21
"""

import re
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

# Unsubscribe keywords that users typically send to opt out of commercial messages
UNSUBSCRIBE_WORDS: Set[str] = {
    'stop',
    'unsubscribe',
    'cancel',
    'remove',
    'opt-out',
    'optout',
    'stop all',
    'end',
    'quit',
}

# Regex patterns that indicate an unsubscribe confirmation message
# These patterns are more specific to avoid false positives from questions
# like "Why do you want to unsubscribe?"
CONFIRMATION_PATTERNS: List[str] = [
    r'(you\s+have\s+been|you\'ve\s+been|successfully)\s+unsubscribed',
    r'(you\s+have\s+been|you\'ve\s+been|successfully)\s+opted.?out',
    r'opted.?out\s+successfully',
    r'removed\s+from',
    r'no\s+longer\s+receive',
    r'will\s+not\s+receive',
    r"won't\s+receive",
    r'been\s+removed',
    r'stop\s+receiving',
    r'preferences?\s+updated',
    r'you\s+have\s+been\s+(removed|unsubscribed)',
    r'^unsubscribed?d?\.?$',  # Single word "Unsubscribed" as entire message
    r'unsubscribe\s+successful',
]


def is_unsubscribe_word(text: str) -> bool:
    """
    Check if text contains ONLY an unsubscribe word (no additional content).

    This is strict: the message must be EXACTLY an unsubscribe word, not just
    contain one. This prevents false positives from normal conversations that
    happen to include "stop" or other words.

    Args:
        text: The message text to check

    Returns:
        True if text is exactly an unsubscribe word (case-insensitive), False otherwise

    Examples:
        >>> is_unsubscribe_word("STOP")
        True
        >>> is_unsubscribe_word("  stop  ")
        True
        >>> is_unsubscribe_word("Please stop")
        False
    """
    if not text:
        return False

    # Normalize: strip whitespace and convert to lowercase
    normalized = text.strip().lower()

    # Check if normalized text is exactly one of the unsubscribe words
    return normalized in UNSUBSCRIBE_WORDS


def is_confirmation_message(text: str) -> bool:
    """
    Check if text appears to be an unsubscribe confirmation message.

    Uses regex patterns to detect common confirmation phrases like
    "You have been unsubscribed" or "You will no longer receive messages".

    Args:
        text: The message text to check

    Returns:
        True if text matches confirmation patterns, False otherwise

    Examples:
        >>> is_confirmation_message("You have been unsubscribed")
        True
        >>> is_confirmation_message("Hello there")
        False
    """
    if not text:
        return False

    text_lower = text.lower()

    # Check if any confirmation pattern matches
    for pattern in CONFIRMATION_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False


def is_commercial_conversation(messages: List[Dict], my_identifier: str) -> bool:
    """
    Determine if a conversation appears to be commercial/spam based on message patterns.

    A conversation is commercial if:
    1. There is at least one message from another party
    2. There is exactly ONE message from the user that is ONLY an unsubscribe word
    3. After the unsubscribe, there are either:
       - No further messages, OR
       - Only confirmation messages
    4. Before the unsubscribe, there is NO real back-and-forth conversation

    The key insight: commercial conversations are one-sided (spam → STOP → optional confirmation).
    Real conversations have dialogue before or after the unsubscribe.

    Args:
        messages: List of message dictionaries with keys:
            - timestamp: Unix timestamp in milliseconds
            - sender: Sender identifier (phone, alias, or "Me")
            - text: Message content
            - Optional: attachments, formatted_time, etc.
        my_identifier: How the user is identified in messages (typically "Me")

    Returns:
        True if conversation appears to be commercial, False otherwise

    Examples:
        >>> messages = [
        ...     {"timestamp": 1000, "sender": "+15551234567", "text": "Sale!"},
        ...     {"timestamp": 2000, "sender": "Me", "text": "STOP"},
        ... ]
        >>> is_commercial_conversation(messages, "Me")
        True

        >>> messages = [
        ...     {"timestamp": 1000, "sender": "Alice", "text": "How are you?"},
        ...     {"timestamp": 2000, "sender": "Me", "text": "Good!"},
        ...     {"timestamp": 3000, "sender": "Alice", "text": "STOP by later"},
        ... ]
        >>> is_commercial_conversation(messages, "Me")
        False
    """
    # Edge case: empty or very short conversations
    if not messages or len(messages) < 2:
        return False

    # Sort messages by timestamp to ensure chronological order
    sorted_messages = sorted(messages, key=lambda m: m.get("timestamp", 0))

    # Find the user's unsubscribe message (if any)
    unsubscribe_index = None
    user_message_count = 0

    for i, msg in enumerate(sorted_messages):
        sender = msg.get("sender", "")
        text = msg.get("text", "")

        if sender == my_identifier:
            user_message_count += 1

            # Check if this message is ONLY an unsubscribe word
            if is_unsubscribe_word(text):
                unsubscribe_index = i
                # Don't break - we want to count ALL user messages

    # No unsubscribe word found
    if unsubscribe_index is None:
        return False

    # If user has multiple messages besides the unsubscribe, it's likely a real conversation
    # Exception: multiple unsubscribe attempts are OK
    other_user_messages = 0
    for msg in sorted_messages:
        if msg.get("sender") == my_identifier:
            if not is_unsubscribe_word(msg.get("text", "")):
                other_user_messages += 1

    if other_user_messages > 0:
        # User sent real messages (not just STOP), so it's a real conversation
        return False

    # Check messages BEFORE the unsubscribe
    messages_before = sorted_messages[:unsubscribe_index]

    # There must be at least one message from the other party before STOP
    if not messages_before:
        return False

    # All messages before unsubscribe should be from the other party (spam)
    for msg in messages_before:
        if msg.get("sender") == my_identifier:
            # User sent a message before STOP - this is a real conversation
            return False

    # Check messages AFTER the unsubscribe
    messages_after = sorted_messages[unsubscribe_index + 1:]

    # If no messages after STOP, it's commercial (spam → STOP, end)
    if not messages_after:
        return True

    # Check if all messages after STOP are confirmation messages
    for msg in messages_after:
        text = msg.get("text", "")
        sender = msg.get("sender", "")

        # If sender is the user, and it's not an unsubscribe word, it's a real conversation
        if sender == my_identifier and not is_unsubscribe_word(text):
            return False

        # If sender is other party, message must be a confirmation
        if sender != my_identifier and not is_confirmation_message(text):
            # Other party sent a non-confirmation message after STOP
            # This suggests real conversation (e.g., "Why are you leaving?")
            return False

    # All checks passed: this appears to be a commercial conversation
    logger.debug(
        f"Detected commercial conversation: "
        f"{len(messages_before)} spam message(s) → STOP → "
        f"{len(messages_after)} confirmation message(s)"
    )
    return True
