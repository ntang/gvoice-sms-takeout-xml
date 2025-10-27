"""
Keyword protection system for conversation filtering.

This module provides keyword-based protection to prevent important conversations
from being archived. Any conversation matching protected keywords will be
excluded from archiving, regardless of spam/commercial detection patterns.

Architecture: Protected-First
- Keyword protection is checked BEFORE any filtering logic
- Matching conversations are immediately protected from archiving
- Enables aggressive filtering with safety guarantees
"""

import json
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class KeywordProtection:
    """
    Protects conversations matching keywords from being archived.

    Supports:
    - Case-sensitive and case-insensitive matching
    - Partial and exact matching
    - Regular expression patterns
    - Category-based organization

    Example:
        protection = KeywordProtection(Path("protected_keywords.json"))
        is_protected, keyword = protection.is_protected(messages)
        if is_protected:
            print(f"Protected by keyword: {keyword}")
    """

    def __init__(self, keywords_file: Path):
        """
        Initialize keyword protection from JSON file.

        Args:
            keywords_file: Path to protected_keywords.json file

        Raises:
            FileNotFoundError: If keywords file doesn't exist
            ValueError: If JSON is invalid or missing required fields
        """
        self.keywords_file = keywords_file
        self.keywords: List[str] = []
        self.regex_patterns: List[re.Pattern] = []
        self.case_sensitive: bool = False
        self.match_partial: bool = True
        self.categories: Dict[str, List[str]] = {}

        self._load_keywords()

        logger.info(
            f"Loaded {len(self.keywords)} keywords and {len(self.regex_patterns)} "
            f"regex patterns from {keywords_file.name}"
        )

    def _load_keywords(self) -> None:
        """
        Load keywords from JSON file.

        Expected JSON structure:
        {
            "case_sensitive": false,
            "match_partial": true,
            "keywords": {
                "category1": ["keyword1", "keyword2"],
                "category2": ["keyword3"]
            },
            "regex_patterns": ["pattern1", "pattern2"]
        }

        Raises:
            FileNotFoundError: If keywords file doesn't exist
            ValueError: If JSON is invalid
        """
        if not self.keywords_file.exists():
            raise FileNotFoundError(
                f"Keywords file not found: {self.keywords_file}\n"
                f"Create this file with protected keywords to enable keyword protection."
            )

        try:
            data = json.loads(self.keywords_file.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.keywords_file}: {e}")

        # Load configuration
        self.case_sensitive = data.get("case_sensitive", False)
        self.match_partial = data.get("match_partial", True)

        # Load keyword categories
        self.categories = data.get("keywords", {})

        # Flatten all categories into single keyword list
        for category, words in self.categories.items():
            if not isinstance(words, list):
                raise ValueError(
                    f"Category '{category}' must contain a list of keywords"
                )
            self.keywords.extend(words)

        # Compile regex patterns
        regex_flags = 0 if self.case_sensitive else re.IGNORECASE
        for pattern_str in data.get("regex_patterns", []):
            try:
                pattern = re.compile(pattern_str, regex_flags)
                self.regex_patterns.append(pattern)
            except re.error as e:
                logger.warning(
                    f"Invalid regex pattern '{pattern_str}': {e} - skipping"
                )

        if not self.keywords and not self.regex_patterns:
            logger.warning(
                f"No keywords or patterns loaded from {self.keywords_file.name}. "
                f"Keyword protection is effectively disabled."
            )

    def is_protected(
        self,
        messages: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if conversation is protected by keyword match.

        Args:
            messages: List of message dicts with 'text' field
                     Expected format: [{'text': 'message content', ...}, ...]

        Returns:
            Tuple of (is_protected, matched_keyword):
            - is_protected: True if any keyword matches
            - matched_keyword: The keyword/pattern that matched, or None

        Example:
            messages = [
                {'text': 'Invoice INV01923-456 attached'},
                {'text': 'Thanks!'}
            ]
            is_protected, keyword = protection.is_protected(messages)
            # Returns: (True, 'INV01923-\\d+')
        """
        # Combine all message text into searchable corpus
        full_text = " ".join(msg.get("text", "") for msg in messages)

        if not full_text.strip():
            return False, None

        # Check simple keywords
        for keyword in self.keywords:
            if self._keyword_matches(keyword, full_text):
                return True, keyword

        # Check regex patterns
        for pattern in self.regex_patterns:
            match = pattern.search(full_text)
            if match:
                matched_text = match.group(0)
                return True, f"{pattern.pattern} (matched: '{matched_text}')"

        return False, None

    def _keyword_matches(self, keyword: str, text: str) -> bool:
        """
        Check if keyword matches text based on configuration.

        Args:
            keyword: The keyword to search for
            text: The text to search in

        Returns:
            True if keyword matches text
        """
        search_text = text if self.case_sensitive else text.lower()
        search_keyword = keyword if self.case_sensitive else keyword.lower()

        if self.match_partial:
            return search_keyword in search_text
        else:
            # Exact match - keyword must be a complete word
            # Use word boundaries to match whole words only
            pattern = re.compile(
                r'\b' + re.escape(search_keyword) + r'\b',
                0 if self.case_sensitive else re.IGNORECASE
            )
            return pattern.search(text) is not None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get keyword protection statistics.

        Returns:
            Dictionary with protection stats:
            - total_keywords: Total number of keywords loaded
            - total_patterns: Total number of regex patterns
            - categories: Number of keyword categories
            - case_sensitive: Whether matching is case-sensitive
            - match_partial: Whether partial matching is enabled
        """
        return {
            "total_keywords": len(self.keywords),
            "total_patterns": len(self.regex_patterns),
            "categories": len(self.categories),
            "case_sensitive": self.case_sensitive,
            "match_partial": self.match_partial,
            "keywords_file": str(self.keywords_file)
        }

    def test_keyword(self, test_text: str) -> Tuple[bool, Optional[str]]:
        """
        Test if a single text string would be protected.

        Useful for debugging and validation.

        Args:
            test_text: Text to test

        Returns:
            Tuple of (is_protected, matched_keyword)

        Example:
            is_protected, keyword = protection.test_keyword("Call Mike Daddio")
            # Returns: (True, "Mike Daddio")
        """
        test_message = [{"text": test_text}]
        return self.is_protected(test_message)
