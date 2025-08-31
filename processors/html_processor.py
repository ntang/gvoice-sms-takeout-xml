"""
HTML Processing Module for SMS/MMS conversion.

This module handles HTML file parsing, file type detection, and HTML content processing
for Google Voice takeout files.
"""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import os

logger = logging.getLogger(__name__)


class StringPool:
    """
    Efficient string pooling for commonly used strings and CSS selectors.

    This class provides cached access to frequently used strings and CSS selectors
    to improve performance and reduce memory allocations.
    """

    def __init__(self):
        # CSS selectors for different HTML elements
        self.CSS_SELECTORS = {
            "message": "div[class*='message'], tr[class*='message'], .conversation div, div[class*='sms'], div[class*='text'], tr[class*='sms'], tr[class*='text']",
            "timestamp": "span[class*='timestamp'], time[datetime], span[class*='date'], div[class*='timestamp'], abbr[class*='dt'], span[class*='time']",
            "phone": "a[href^='tel:'], span[class*='phone'], div[class*='phone'], cite[class*='sender'], cite[class*='participant']",
            "sender": "cite[class*='sender'], span[class*='sender'], div[class*='sender']",
            "content": "div[class*='content'], span[class*='content'], p[class*='content'], q, blockquote",
            "participants": "cite[class*='sender'], span[class*='sender'], div[class*='sender'], a[href^='tel:'], span[class*='phone'], div[class*='phone']",
            "vcard": "a[class*='vcard'], span[class*='vcard'], div[class*='vcard']",
            "fn": "span[class*='fn'], abbr[class*='fn'], div[class*='fn']",
            "duration": "span[class*='duration'], abbr[class*='duration'], div[class*='duration']",
            "dt": "abbr[class*='dt'], span[class*='dt'], time[datetime]",
        }

        # Additional selectors for specific elements
        self.ADDITIONAL_SELECTORS = {
            "tel_links": "a.tel[href], a[href*='tel:']",
            "img_src": "img[src]",
            "vcard_links": "a.vcard[href], a[href*='vcard']",
            "fn_elements": "span.fn, abbr.fn, div.fn, .fn",
            "dt_elements": "abbr.dt, .dt, time[datetime]",
            "published_elements": "abbr.published, .published, time[datetime]",
            "time_elements": "time[datetime], span[datetime], abbr[title]",
            "duration_elements": "abbr.duration, .duration",
            "transcription_elements": ".message, .transcription, .content",
        }

        # Common patterns used in HTML content
        self.PATTERNS = {
            "tel_href": "tel:",
            "group_marker": "Group conversation with:",
            "voicemail_prefix": "🎙️",
            "call_prefix": "📞",
        }

        # File extensions for different types
        self.FILE_EXTENSIONS = {
            "html": ".html",
            "xml": ".xml",
            "jpg": ".jpg",
            "jpeg": ".jpeg",
            "png": ".png",
            "gif": ".gif",
            "vcf": ".vcf",
        }

        # XML attributes and values
        self.XML_ATTRS = {
            "protocol": "0",
            "address": "",
            "type": "",
            "subject": "null",
            "body": "",
            "toa": "null",
            "sc_toa": "null",
            "date": "",
            "read": "1",
            "status": "-1",
            "locked": "0",
        }

        # HTML classes and attributes
        self.HTML_CLASSES = {
            "dt": "dt",
            "tel": "tel",
            "sender": "sender",
            "message": "message",
            "timestamp": "timestamp",
            "participants": "participants",
            "vcard": "vcard",
            "fn": "fn",
            "duration": "duration",
        }

        # Common timestamp indicators for early exit optimization
        self.TIMESTAMP_INDICATORS = ["202", "201", "200", "199", "198", "197"]

        # Common timestamp classes and IDs for faster lookup
        self.TIMESTAMP_CLASSES = [
            "timestamp",
            "date",
            "time",
            "when",
            "posted",
            "created",
        ]
        self.TIMESTAMP_IDS = ["timestamp", "date", "time", "when", "posted", "created"]
        self.DATA_ATTRS = ["data-timestamp", "data-date", "data-time", "data-when"]

        # Common patterns for file type detection and processing
        self.PATTERNS = {
            "tel_href": "tel:",
            "group_marker": "Group conversation with:",
            "voicemail_prefix": "🎙️",
            "call_prefix": "📞",
        }

        # Common patterns for file type detection
        self.FILE_PATTERNS = {
            "sms": r".*Text.*\.html$",
            "mms": r".*MMS.*\.html$",
            "call": r".*(Placed|Received|Missed).*\.html$",
            "voicemail": r".*Voicemail.*\.html$",
        }

        # HTML parser configuration
        self.HTML_PARSER = "html.parser"

        # File read buffer size for performance
        self.FILE_READ_BUFFER_SIZE = 8192


# Global string pool instance
STRING_POOL = StringPool()


def parse_html_file(html_file: Path) -> BeautifulSoup:
    """
    Parse an HTML file and return a BeautifulSoup object.

    Args:
        html_file: Path to the HTML file

    Returns:
        BeautifulSoup object for the HTML content

    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: For other parsing errors
    """
    try:
        with open(
            html_file,
            "r",
            encoding="utf-8",
            buffering=STRING_POOL.FILE_READ_BUFFER_SIZE,
        ) as file:
            soup = BeautifulSoup(file, STRING_POOL.HTML_PARSER)
            return soup
    except FileNotFoundError:
        logger.error(f"HTML file not found: {html_file}")
        raise
    except Exception as e:
        logger.error(f"Failed to parse HTML file {html_file}: {e}")
        raise


def get_file_type(filename: str) -> str:
    """
    Determine the type of HTML file based on its filename.

    Args:
        filename: Name of the file to analyze

    Returns:
        String indicating the file type: "sms_mms", "call", "voicemail", or "unknown"
    """
    filename_lower = filename.lower()

    # Check for specific patterns in filename
    if any(re.search(pattern, filename_lower) for pattern in [r"text", r"sms"]):
        return "sms_mms"  # Changed from "sms" to "sms_mms" to match file_processor.py expectations
    elif any(re.search(pattern, filename_lower) for pattern in [r"mms", r"multimedia"]):
        return "sms_mms"  # MMS files should also be processed as SMS/MMS
    elif any(
        re.search(pattern, filename_lower)
        for pattern in [r"placed", r"received", r"missed"]
    ):
        return "call"
    elif any(
        re.search(pattern, filename_lower) for pattern in [r"voicemail", r"voice"]
    ):
        return "voicemail"
    else:
        # Default to SMS/MMS for unknown types (most files are SMS/MMS)
        return "sms_mms"


def should_skip_file(filename: str) -> bool:
    """
    Determine if a file should be skipped based on its name or characteristics.

    Args:
        filename: Name of the file to check

    Returns:
        True if the file should be skipped, False otherwise
    """
    # Skip files that are clearly corrupted or invalid
    skip_patterns = [
        r"^\.",  # Hidden files
        r"~$",  # Backup files
        r"\.tmp$",  # Temporary files
        r"\.bak$",  # Backup files
        r"corrupt",  # Corrupted files
        r"invalid",  # Invalid files
    ]

    filename_lower = filename.lower()
    return any(re.search(pattern, filename_lower) for pattern in skip_patterns)


def extract_own_phone_number(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract the user's own phone number from the HTML content.

    Args:
        soup: BeautifulSoup object of the HTML content

    Returns:
        The user's phone number if found, None otherwise
    """
    try:
        # Look for common patterns where own number might be stored
        own_number_selectors = [
            "div[class*='own']",
            "span[class*='own']",
            "div[class*='user']",
            "span[class*='user']",
            "div[class*='me']",
            "span[class*='me']",
        ]

        for selector in own_number_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                # Look for phone number patterns in the text
                phone_match = re.search(
                    r"\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})", text
                )
                if phone_match:
                    return phone_match.group(0)

        # If no specific selectors work, try to find any phone number in the document
        all_text = soup.get_text()
        phone_match = re.search(
            r"\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})", all_text
        )
        if phone_match:
            return phone_match.group(0)

        return None

    except Exception as e:
        logger.debug(f"Failed to extract own phone number: {e}")
        return None


def validate_html_structure(soup: BeautifulSoup, filename: str) -> bool:
    """
    Validate that the HTML structure is as expected for Google Voice files.

    Args:
        soup: BeautifulSoup object of the HTML content
        filename: Name of the file being validated

    Returns:
        True if the HTML structure is valid, False otherwise
    """
    try:
        # Check for basic HTML structure
        if not soup.find("html"):
            logger.debug(f"File {filename} does not contain <html> tag")
            return False

        # Check for body content
        if not soup.find("body"):
            logger.debug(f"File {filename} does not contain <body> tag")
            return False

        # Check for some content (not just empty structure)
        if not soup.get_text().strip():
            logger.debug(f"File {filename} appears to be empty")
            return False

        return True

    except Exception as e:
        logger.debug(f"Failed to validate HTML structure for {filename}: {e}")
        return False


def get_html_file_info(html_file: Path) -> Dict[str, Any]:
    """
    Get comprehensive information about an HTML file.

    Args:
        html_file: Path to the HTML file

    Returns:
        Dictionary containing file information
    """
    try:
        file_info = {
            "path": str(html_file),
            "name": html_file.name,
            "size": html_file.stat().st_size,
            "type": get_file_type(html_file.name),
            "should_skip": should_skip_file(html_file.name),
            "exists": html_file.exists(),
            "readable": html_file.is_file() and os.access(html_file, os.R_OK),
        }

        # Try to parse the HTML to get additional info
        if file_info["readable"] and not file_info["should_skip"]:
            try:
                soup = parse_html_file(html_file)
                file_info["html_valid"] = validate_html_structure(soup, html_file.name)
                file_info["own_number"] = extract_own_phone_number(soup)
            except Exception as e:
                file_info["html_valid"] = False
                file_info["parse_error"] = str(e)
        else:
            file_info["html_valid"] = False

        return file_info

    except Exception as e:
        logger.error(f"Failed to get file info for {html_file}: {e}")
        return {"path": str(html_file), "name": html_file.name, "error": str(e)}
