"""
Unit tests for keyword protection system.

This module tests the keyword-based protection system that prevents important
conversations from being archived. Tests cover keyword matching, regex patterns,
conversation ID (filename) matching, and error handling.

Test Coverage:
- Conversation ID matching (validates bef661a fix)
- Exact and partial keyword matching
- Case-sensitive vs case-insensitive matching
- Regex pattern matching
- Error handling (malformed JSON, missing files)
- Edge cases

Author: Claude Code
Date: 2025-10-26
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import List, Dict

from core.keyword_protection import KeywordProtection


class TestConversationIDMatching:
    """
    Test conversation ID (filename) matching functionality.

    These tests validate the fix in commit bef661a where conversation IDs
    are checked for keyword matches in addition to message content.
    """

    def test_conversation_id_keyword_match(self, tmp_path):
        """
        Test that keywords match conversation IDs with underscore conversion.

        Validates: "Ed_Harbur" filename matches "Ed Harbur" keyword
        """
        # Create test keywords file
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["Ed Harbur", "Phil Penney"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        # Initialize protection
        protection = KeywordProtection(keywords_file)

        # Test: Conversation ID "Ed_Harbur" should match "Ed Harbur" keyword
        messages = [{"text": "Ok"}]  # Generic message, keyword only in ID
        is_protected, keyword = protection.is_protected(
            messages,
            conversation_id="Ed_Harbur"
        )

        assert is_protected is True
        assert "Ed Harbur" in keyword

    def test_conversation_id_underscore_conversion(self, tmp_path):
        """
        Test complex conversation IDs with multiple underscores.

        Validates: "Ed_Harbur_Phil_CSHC" matches multiple keywords
        """
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "contractors": ["Ed Harbur", "CSHC", "Phil Penney"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Test: Should match "CSHC" in "Ed_Harbur_Phil_CSHC"
        messages = [{"text": "Thanks"}, {"text": "See you"}]
        is_protected, keyword = protection.is_protected(
            messages,
            conversation_id="Ed_Harbur_Phil_CSHC"
        )

        assert is_protected is True
        # Should match one of the keywords
        assert any(k in keyword.lower() for k in ["ed harbur", "cshc", "phil"])

    def test_conversation_id_phone_number_no_match(self, tmp_path):
        """
        Test that phone numbers as conversation IDs don't false-positive.

        Validates: "+15551234567" doesn't match unrelated keywords
        """
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["John Doe", "Jane Smith"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Phone number conversation ID with no keyword in messages
        messages = [{"text": "Stop"}]
        is_protected, keyword = protection.is_protected(
            messages,
            conversation_id="+15551234567"
        )

        assert is_protected is False
        assert keyword is None


class TestKeywordMatching:
    """Test core keyword matching functionality."""

    def test_exact_keyword_match(self, tmp_path):
        """Test exact keyword match in message text."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["Mike Daddio"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        messages = [{"text": "Call Mike Daddio tomorrow"}]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is True
        assert "Mike Daddio" in keyword

    def test_partial_keyword_match(self, tmp_path):
        """
        Test partial keyword matching (match_partial: true).

        Validates: "Mike Daddio Inc" matches "Mike Daddio"
        """
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "companies": ["Acme Corporation"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # "Acme Corporation Inc" should match "Acme Corporation"
        messages = [{"text": "Meeting with Acme Corporation Inc tomorrow"}]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is True
        assert "Acme Corporation" in keyword

    def test_multiple_messages_keyword_match(self, tmp_path):
        """Test keyword found in any message of conversation."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "terms": ["confidential"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Keyword in third message
        messages = [
            {"text": "Hello"},
            {"text": "How are you?"},
            {"text": "This is confidential information"}
        ]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is True
        assert "confidential" in keyword.lower()

    def test_no_keyword_match(self, tmp_path):
        """Test that conversation without keywords is not protected."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["John Doe"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        messages = [{"text": "Hello"}, {"text": "Thanks"}]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is False
        assert keyword is None

    def test_case_insensitive_match(self, tmp_path):
        """Test case-insensitive matching (default behavior)."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["mike daddio"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # All variations should match
        test_cases = [
            [{"text": "Call MIKE DADDIO"}],
            [{"text": "Call Mike Daddio"}],
            [{"text": "Call mike daddio"}],
            [{"text": "Call MiKe DaDdIo"}]
        ]

        for messages in test_cases:
            is_protected, keyword = protection.is_protected(messages)
            assert is_protected is True, f"Failed for: {messages[0]['text']}"

    def test_case_sensitive_match(self, tmp_path):
        """Test case-sensitive matching when enabled."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": True,
            "match_partial": True,
            "keywords": {
                "people": ["Mike Daddio"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Exact case should match
        messages = [{"text": "Call Mike Daddio"}]
        is_protected, keyword = protection.is_protected(messages)
        assert is_protected is True

        # Different case should NOT match
        messages = [{"text": "Call MIKE DADDIO"}]
        is_protected, keyword = protection.is_protected(messages)
        assert is_protected is False


class TestRegexPatterns:
    """Test regex pattern matching."""

    def test_regex_pattern_match(self, tmp_path):
        """Test basic regex pattern matching."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {},
            "regex_patterns": ["INV\\d{4,}"]
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Should match invoice number pattern
        messages = [{"text": "Invoice INV01923-456 attached"}]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is True
        assert "INV" in keyword

    def test_multiple_regex_patterns(self, tmp_path):
        """Test multiple regex patterns."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {},
            "regex_patterns": [
                "INV\\d{4,}",
                "PO-\\d{4,}",
                "\\$\\d{4,}"
            ]
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Test each pattern
        test_cases = [
            ([{"text": "Invoice INV12345"}], True, "INV"),
            ([{"text": "Purchase Order PO-5678"}], True, "PO-"),
            ([{"text": "Amount: $50000"}], True, "$"),
            ([{"text": "No match here"}], False, None)
        ]

        for messages, should_match, expected_pattern in test_cases:
            is_protected, keyword = protection.is_protected(messages)
            assert is_protected == should_match
            if should_match:
                assert expected_pattern in keyword

    def test_regex_with_keywords(self, tmp_path):
        """Test that both regex and keywords work together."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["John Doe"]
            },
            "regex_patterns": ["INV\\d{4,}"]
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Test keyword match
        messages = [{"text": "Call John Doe"}]
        is_protected, keyword = protection.is_protected(messages)
        assert is_protected is True
        assert "John Doe" in keyword

        # Test regex match
        messages = [{"text": "Invoice INV12345"}]
        is_protected, keyword = protection.is_protected(messages)
        assert is_protected is True
        assert "INV" in keyword


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_keyword_file_malformed_json(self, tmp_path):
        """Test that malformed JSON raises ValueError with helpful message."""
        keywords_file = tmp_path / "malformed.json"
        keywords_file.write_text("{invalid json content")

        with pytest.raises(ValueError, match="Invalid JSON"):
            KeywordProtection(keywords_file)

    def test_keyword_file_missing(self, tmp_path):
        """Test that missing file raises FileNotFoundError with helpful message."""
        keywords_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="Keywords file not found"):
            KeywordProtection(keywords_file)

    def test_empty_keywords_file_behavior(self, tmp_path):
        """Test graceful handling of empty keywords file."""
        keywords_file = tmp_path / "empty.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {},
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        # Should initialize without error
        protection = KeywordProtection(keywords_file)

        # Should not match anything
        messages = [{"text": "Any message"}]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is False
        assert keyword is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_message_list(self, tmp_path):
        """Test empty message list."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["John Doe"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        messages = []
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is False
        assert keyword is None

    def test_messages_with_empty_text(self, tmp_path):
        """Test messages with empty text fields."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["John Doe"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        messages = [{"text": ""}, {"text": "   "}, {"text": None}]
        is_protected, keyword = protection.is_protected(messages)

        assert is_protected is False

    def test_get_stats_method(self, tmp_path):
        """Test get_stats() returns correct statistics."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "category1": ["keyword1", "keyword2"],
                "category2": ["keyword3"]
            },
            "regex_patterns": ["pattern1", "pattern2"]
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)
        stats = protection.get_stats()

        assert stats["total_keywords"] == 3
        assert stats["total_patterns"] == 2
        assert stats["categories"] == 2
        assert stats["case_sensitive"] is False
        assert stats["match_partial"] is True

    def test_test_keyword_method(self, tmp_path):
        """Test test_keyword() convenience method."""
        keywords_file = tmp_path / "test_keywords.json"
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["Mike Daddio"]
            },
            "regex_patterns": []
        }
        keywords_file.write_text(json.dumps(keywords_data))

        protection = KeywordProtection(keywords_file)

        # Test with message text only
        is_protected, keyword = protection.test_keyword("Call Mike Daddio")
        assert is_protected is True

        # Test with conversation ID
        is_protected, keyword = protection.test_keyword("Ok", conversation_id="Mike_Daddio")
        assert is_protected is True

        # Test no match
        is_protected, keyword = protection.test_keyword("Hello")
        assert is_protected is False
