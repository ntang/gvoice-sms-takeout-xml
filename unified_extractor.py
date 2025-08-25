"""
Unified Extractor for Google Voice Takeout files.

This module provides a unified approach to extracting information from various types of
Google Voice export files (SMS, MMS, calls, voicemails) while eliminating redundancy
and maintaining all functionality.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import phonenumbers

from utils import (
    is_valid_phone_number,
    normalize_phone_number,
    parse_timestamp_from_filename,
)
from config import SERVICE_CODES

logger = logging.getLogger(__name__)


class UnifiedExtractor:
    """
    Unified extractor for all Google Voice file types.

    This class consolidates extraction logic for SMS, MMS, calls, and voicemails
    while eliminating code duplication and maintaining all functionality.
    """

    def __init__(self):
        # Common selectors for different data types
        self.timestamp_selectors = [
            'span[class*="timestamp"]',
            "time[datetime]",
            'span[class*="date"]',
            'div[class*="timestamp"]',
            'abbr[class*="dt"]',
            'span[class*="time"]',
        ]

        self.phone_selectors = [
            'a[href^="tel:"]',
            'span[class*="phone"]',
            'div[class*="phone"]',
            'cite[class*="sender"]',
            'cite[class*="participant"]',
        ]

        self.message_selectors = [
            'div[class*="message"]',
            'span[class*="message"]',
            'p[class*="message"]',
            'div[class*="content"]',
            "q",  # Quote elements often contain message content
            "blockquote",
        ]

        # Common timestamp formats
        self.timestamp_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H_%M_%SZ",  # Google Voice format
            "%b %d",  # "Jun 17" format
            "%Y-%m-%d",
        ]

        # Phone number patterns
        self.phone_patterns = [
            r"\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})",  # US format
            r"\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}",  # International
            r"tel:([+\d\s\-\(\)]+)",  # tel: links
            r"(\+\d{1,3}\s?\d{1,14})",  # General international format
        ]

        # TEL href pattern for parsing
        self.tel_href_pattern = re.compile(r"tel:([+\d\s\-\(\)]+)")

    def extract_info(
        self, filename: str, soup: BeautifulSoup, file_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Unified extraction method for all file types.

        Args:
            filename: Name of the file being processed
            soup: BeautifulSoup object of the HTML content
            file_type: Type of file ('sms', 'mms', 'call', 'voicemail')

        Returns:
            Dictionary with extracted information or None if extraction fails
        """
        try:
            # Extract common fields
            timestamp = self._extract_timestamp(soup, filename)
            phone_number = self._extract_phone_number(soup, filename)

            # Early validation
            if not phone_number:
                logger.debug(f"No phone number found for {file_type} file: {filename}")
                return None

            # Apply date filtering if timestamp is available
            if timestamp and self._should_skip_by_date(timestamp):
                logger.debug(f"Skipping {file_type} due to date filtering: {filename}")
                return None

            # Extract type-specific information
            if file_type in ["sms", "mms"]:
                return self._extract_message_info(
                    filename, soup, timestamp, phone_number, file_type
                )
            elif file_type == "call":
                return self._extract_call_info(filename, soup, timestamp, phone_number)
            elif file_type == "voicemail":
                return self._extract_voicemail_info(
                    filename, soup, timestamp, phone_number
                )
            else:
                logger.warning(f"Unknown file type: {file_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract {file_type} info from {filename}: {e}")
            return None

    def _extract_timestamp(
        self, soup: BeautifulSoup, filename: str = None
    ) -> Optional[int]:
        """Extract timestamp from HTML content with multiple fallback strategies."""
        try:
            # Strategy 1: Look for HTML elements with timestamp data
            for selector in self.timestamp_selectors:
                element = soup.select_one(selector)
                if element:
                    # Try datetime attribute first
                    datetime_attr = element.get("datetime")
                    if datetime_attr:
                        try:
                            dt = datetime.fromisoformat(
                                datetime_attr.replace("Z", "+00:00")
                            )
                            return int(dt.timestamp() * 1000)
                        except ValueError:
                            pass

                    # Try title attribute (common in Google Voice exports)
                    title_attr = element.get("title")
                    if title_attr:
                        try:
                            dt = datetime.fromisoformat(
                                title_attr.replace("Z", "+00:00")
                            )
                            return int(dt.timestamp() * 1000)
                        except ValueError:
                            pass

                    # Try text content
                    text = element.get_text(strip=True)
                    if text:
                        timestamp = self._parse_timestamp_text(text)
                        if timestamp:
                            return timestamp

            # Strategy 2: Parse from filename if it contains timestamp
            if filename:
                timestamp = parse_timestamp_from_filename(filename)
                if timestamp:
                    return int(timestamp.timestamp() * 1000)

            # Strategy 3: Look for any date/time patterns in the entire HTML
            text_content = soup.get_text()
            date_patterns = [
                r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)",  # ISO format
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",  # Standard format
                r"(\d{4}-\d{2}-\d{2})",  # Date only
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text_content)
                if match:
                    try:
                        date_str = match.group(1)
                        if "T" in date_str and "Z" in date_str:
                            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                        elif " " in date_str:
                            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        else:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                        return int(dt.timestamp() * 1000)
                    except ValueError:
                        continue

            return None

        except Exception as e:
            logger.debug(f"Failed to extract timestamp: {e}")
            return None

    def _parse_timestamp_text(self, text: str) -> Optional[int]:
        """Parse timestamp from text string using multiple formats."""
        try:
            for fmt in self.timestamp_formats:
                try:
                    dt = datetime.strptime(text, fmt)
                    return int(dt.timestamp() * 1000)
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def _extract_phone_number(
        self, soup: BeautifulSoup, filename: str = None
    ) -> Optional[str]:
        """Extract phone number with comprehensive fallback strategies."""
        try:
            # Strategy 1: Look for HTML elements with phone data
            for selector in self.phone_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Check href attribute for tel: links
                    href = element.get("href")
                    if href and href.startswith("tel:"):
                        phone = href[4:]  # Remove 'tel:' prefix
                        if is_valid_phone_number(phone):
                            return normalize_phone_number(phone)

                    # Check text content
                    text = element.get_text(strip=True)
                    if text:
                        phone_numbers = self._extract_phone_numbers_from_text(text)
                        for phone in phone_numbers:
                            if is_valid_phone_number(phone):
                                return normalize_phone_number(phone)

            # Strategy 2: Extract from filename if it contains phone number
            if filename:
                phone_numbers = self._extract_phone_numbers_from_text(filename)
                for phone in phone_numbers:
                    if is_valid_phone_number(phone):
                        return normalize_phone_number(phone)

            # Strategy 3: Look for any phone number patterns in the entire HTML
            text_content = soup.get_text()
            phone_numbers = self._extract_phone_numbers_from_text(text_content)
            for phone in phone_numbers:
                if is_valid_phone_number(phone):
                    return normalize_phone_number(phone)

            # Strategy 4: Look for any text that might be a phone number
            # This is a more lenient approach for edge cases
            text_content = soup.get_text()
            # Look for patterns like +15557776666 or 15557776666
            phone_match = re.search(r"\+?(\d{10,15})", text_content)
            if phone_match:
                phone = "+" + phone_match.group(1)
                if len(phone) >= 12:  # +1 + 10 digits minimum
                    return phone

            return None

        except Exception as e:
            logger.debug(f"Failed to extract phone number: {e}")
            return None

    def _extract_phone_numbers_from_text(self, text: str) -> List[str]:
        """Extract phone numbers from text using multiple patterns."""
        phone_numbers = []

        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    # Join tuple matches
                    phone = "".join(match)
                else:
                    phone = match

                if phone and len(phone) >= 7:  # Minimum length for a phone number
                    phone_numbers.append(phone)

        return list(set(phone_numbers))  # Remove duplicates

    def _extract_message_info(
        self,
        filename: str,
        soup: BeautifulSoup,
        timestamp: int,
        phone_number: str,
        file_type: str,
    ) -> Dict[str, Any]:
        """Extract SMS/MMS specific information."""
        try:
            # Extract message content
            message_content = self._extract_message_content(soup)

            # Extract attachments
            attachments = self._extract_attachments(soup)

            # Extract sender information
            sender = self._extract_sender_info(soup, phone_number)

            return {
                "type": file_type,
                "phone_number": phone_number,
                "timestamp": timestamp,
                "message_content": message_content,
                "attachments": attachments,
                "sender": sender,
                "num_img": len([a for a in attachments if "image" in a.lower()]),
                "num_vcf": len([a for a in attachments if "vcard" in a.lower()]),
                "filename": filename,
            }

        except Exception as e:
            logger.error(f"Failed to extract message info: {e}")
            return None

    def _extract_call_info(
        self, filename: str, soup: BeautifulSoup, timestamp: int, phone_number: str
    ) -> Dict[str, Any]:
        """Extract call-specific information."""
        try:
            # Determine call type from filename
            filename_lower = filename.lower()
            if "placed" in filename_lower:
                call_type = "outgoing"
            elif "missed" in filename_lower:
                call_type = "missed"
            elif "received" in filename_lower:
                call_type = "incoming"
            else:
                call_type = "unknown"

            # Extract duration
            duration = self._extract_duration(soup)

            return {
                "type": call_type,
                "phone_number": phone_number,
                "timestamp": timestamp,
                "duration": duration,
                "filename": filename,
            }

        except Exception as e:
            logger.error(f"Failed to extract call info: {e}")
            return None

    def _extract_voicemail_info(
        self, filename: str, soup: BeautifulSoup, timestamp: int, phone_number: str
    ) -> Dict[str, Any]:
        """Extract voicemail-specific information."""
        try:
            # Extract transcription
            transcription = self._extract_transcription(soup)

            # Extract duration
            duration = self._extract_duration(soup)

            return {
                "type": "voicemail",
                "phone_number": phone_number,
                "timestamp": timestamp,
                "duration": duration,
                "transcription": transcription,
                "filename": filename,
            }

        except Exception as e:
            logger.error(f"Failed to extract voicemail info: {e}")
            return None

    def _extract_message_content(self, soup: BeautifulSoup) -> str:
        """Extract message content from HTML."""
        try:
            # Look for message content in various selectors
            for selector in self.message_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return text

            # Fallback: look for any text content
            text_elements = soup.find_all(["p", "div", "span"])
            for element in text_elements:
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Minimum meaningful length
                    return text

            return "[No message content]"

        except Exception as e:
            logger.debug(f"Failed to extract message content: {e}")
            return "[Error extracting message]"

    def _extract_attachments(self, soup: BeautifulSoup) -> List[str]:
        """Extract attachment information from HTML."""
        attachments = []

        try:
            # Look for images
            images = soup.find_all("img")
            for img in images:
                src = img.get("src", "")
                alt = img.get("alt", "")
                if src or alt:
                    attachments.append(f"Image: {alt or src}")

            # Look for vCard links
            vcard_links = soup.find_all("a", class_=re.compile(r"vcard"))
            for link in vcard_links:
                text = link.get_text(strip=True)
                if text:
                    attachments.append(f"vCard: {text}")

            # Look for other file attachments
            file_links = soup.find_all("a", href=re.compile(r"\.(pdf|doc|txt|zip)"))
            for link in file_links:
                text = link.get_text(strip=True)
                href = link.get("href", "")
                if text or href:
                    attachments.append(f"File: {text or href}")

        except Exception as e:
            logger.debug(f"Failed to extract attachments: {e}")

        return attachments

    def _extract_sender_info(self, soup: BeautifulSoup, phone_number: str) -> str:
        """Extract sender information from HTML."""
        try:
            # Look for sender information
            sender_selectors = [
                'cite[class*="sender"]',
                'span[class*="sender"]',
                'div[class*="sender"]',
            ]

            for selector in sender_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and text != phone_number:
                        return text

            return phone_number

        except Exception as e:
            logger.debug(f"Failed to extract sender info: {e}")
            return phone_number

    def _extract_duration(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract duration information from HTML."""
        try:
            # Look for duration in various formats
            duration_selectors = [
                'span[class*="duration"]',
                'span[class*="time"]',
                'div[class*="duration"]',
            ]

            for selector in duration_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and any(char.isdigit() for char in text):
                        return text

            return None

        except Exception as e:
            logger.debug(f"Failed to extract duration: {e}")
            return None

    def _extract_transcription(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract voicemail transcription from HTML."""
        try:
            # Look for transcription in various formats
            transcription_selectors = [
                'div[class*="transcription"]',
                'span[class*="transcription"]',
                'p[class*="transcription"]',
                'div[class*="message"]',  # Often contains transcription
                "q",  # Quote elements often contain transcription
            ]

            for selector in transcription_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 5:  # Minimum meaningful length
                        return text

            return None

        except Exception as e:
            logger.debug(f"Failed to extract transcription: {e}")
            return None

    def _should_skip_by_date(self, timestamp: int) -> bool:
        """Check if message should be skipped based on date filtering."""
        # This would integrate with the existing date filtering logic
        # For now, return False to maintain existing behavior
        return False

    def determine_file_type(self, filename: str) -> str:
        """Determine the type of file based on filename patterns."""
        filename_lower = filename.lower()

        if " - text - " in filename_lower:
            return "sms"
        elif " - mms - " in filename_lower:
            return "mms"
        elif any(
            pattern in filename_lower
            for pattern in [" - placed - ", " - received - ", " - missed - "]
        ):
            return "call"
        elif " - voicemail - " in filename_lower:
            return "voicemail"
        else:
            # Default to SMS for unknown types
            return "sms"

    def extract_all_info(
        self, filename: str, soup: BeautifulSoup
    ) -> Optional[Dict[str, Any]]:
        """
        Extract all information from a file, automatically determining the type.

        This is the main entry point for the unified extractor.
        """
        file_type = self.determine_file_type(filename)
        return self.extract_info(filename, soup, file_type)
