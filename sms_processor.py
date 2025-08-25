"""
SMS Processing Module for Google Voice Takeout conversion.

This module handles the processing of SMS/MMS HTML files from Google Voice Takeout.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from bs4 import BeautifulSoup

from utils import (
    is_valid_phone_number,
    normalize_phone_number,
    parse_timestamp_from_filename,
)
from conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class SMSProcessor:
    """Handles SMS/MMS file processing and conversion."""

    def __init__(self, conversation_manager: ConversationManager):
        self.conversation_manager = conversation_manager

    def process_sms_file(self, html_file: Path, own_number: str) -> Dict[str, int]:
        """Process an SMS HTML file and return statistics."""
        try:
            # Read and parse HTML
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            # Extract SMS information
            sms_info = self._extract_sms_info(html_file.name, soup)
            if not sms_info:
                logger.error(f"Could not extract SMS information from {html_file.name}")
                return {
                    "num_sms": 0,
                    "num_img": 0,
                    "num_vcf": 0,
                    "num_calls": 0,
                    "num_voicemails": 0,
                    "own_number": own_number,
                }

            # Write SMS entry to conversation
            self._write_sms_entry(str(html_file), sms_info, own_number, soup)

            return {
                "num_sms": 1,
                "num_img": sms_info.get("num_img", 0),
                "num_vcf": sms_info.get("num_vcf", 0),
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": own_number,
            }

        except Exception as e:
            logger.error(f"Failed to process SMS file {html_file}: {e}")
            return {
                "num_sms": 0,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": own_number,
            }

    def _extract_sms_info(self, filename: str, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract SMS information from HTML content."""
        try:
            # Extract timestamp
            timestamp = self._extract_timestamp(soup)
            if not timestamp:
                logger.warning(f"No timestamp found in {filename}")
                return None

            # Extract phone number
            phone_number = self._extract_phone_number(soup)
            if not phone_number:
                logger.warning(f"No phone number found in {filename}")
                return None

            # Extract message content
            message_content = self._extract_message_content(soup)

            # Extract attachments
            attachments = self._extract_attachments(soup)

            return {
                "timestamp": timestamp,
                "phone_number": phone_number,
                "message_content": message_content,
                "attachments": attachments,
                "num_img": len([a for a in attachments if "image" in a.lower()]),
                "num_vcf": len([a for a in attachments if "vcard" in a.lower()]),
            }

        except Exception as e:
            logger.error(f"Failed to extract SMS info from {filename}: {e}")
            return None

    def _extract_timestamp(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract timestamp from HTML content."""
        try:
            # Look for timestamp in various formats
            timestamp_selectors = [
                'span[class*="timestamp"]',
                "time[datetime]",
                'span[class*="date"]',
                'div[class*="timestamp"]',
            ]

            for selector in timestamp_selectors:
                element = soup.select_one(selector)
                if element:
                    # Try to get datetime attribute first
                    datetime_attr = element.get("datetime")
                    if datetime_attr:
                        try:
                            dt = datetime.fromisoformat(
                                datetime_attr.replace("Z", "+00:00")
                            )
                            return int(dt.timestamp() * 1000)
                        except ValueError:
                            pass

                    # Try to parse text content
                    text = element.get_text(strip=True)
                    if text:
                        timestamp = self._parse_timestamp_text(text)
                        if timestamp:
                            return timestamp

            return None

        except Exception as e:
            logger.debug(f"Failed to extract timestamp: {e}")
            return None

    def _parse_timestamp_text(self, text: str) -> Optional[int]:
        """Parse timestamp from text string."""
        try:
            # Common timestamp formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%m/%d/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(text, fmt)
                    return int(dt.timestamp() * 1000)
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def _extract_phone_number(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract phone number from HTML content."""
        try:
            # Look for phone number in various formats
            phone_selectors = [
                'a[href^="tel:"]',
                'span[class*="phone"]',
                'div[class*="phone"]',
                'cite[class*="sender"]',
            ]

            for selector in phone_selectors:
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
                        # Extract phone numbers from text
                        phone_numbers = re.findall(r"\+?[\d\s\-\(\)]+", text)
                        for phone in phone_numbers:
                            cleaned = re.sub(r"[\s\-\(\)]", "", phone)
                            if is_valid_phone_number(cleaned):
                                return normalize_phone_number(cleaned)

            return None

        except Exception as e:
            logger.debug(f"Failed to extract phone number: {e}")
            return None

    def _extract_message_content(self, soup: BeautifulSoup) -> str:
        """Extract message content from HTML."""
        try:
            # Look for message content in various selectors
            content_selectors = [
                'div[class*="message"]',
                'span[class*="message"]',
                'p[class*="message"]',
                'div[class*="content"]',
            ]

            for selector in content_selectors:
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

    def _write_sms_entry(
        self, filename: str, sms_info: Dict, own_number: str, soup: BeautifulSoup
    ):
        """Write SMS entry to conversation file."""
        try:
            # Get conversation ID
            conversation_id = self.conversation_manager.get_conversation_id(
                [sms_info["phone_number"]], is_group=False
            )

            # Format message for output
            if self.conversation_manager.output_format == "xml":
                self._write_sms_xml(conversation_id, sms_info)
            else:
                self._write_sms_html(conversation_id, sms_info, soup)

        except Exception as e:
            logger.error(f"Failed to write SMS entry: {e}")

    def _write_sms_xml(self, conversation_id: str, sms_info: Dict):
        """Write SMS entry in XML format."""
        try:
            # Create XML content
            xml_content = f'<sms protocol="0" address="{sms_info["phone_number"]}" '
            xml_content += f'date="{sms_info["timestamp"]}" type="1" '
            xml_content += f'subject="null" body="{sms_info["message_content"]}" '
            xml_content += f'toa="null" sc_toa="null" service_center="null" '
            xml_content += f'read="1" status="-1" locked="0" />\n'

            # Write to conversation file
            self.conversation_manager.write_message(
                conversation_id, xml_content, sms_info["timestamp"]
            )

        except Exception as e:
            logger.error(f"Failed to write SMS XML: {e}")

    def _write_sms_html(
        self, conversation_id: str, sms_info: Dict, soup: BeautifulSoup
    ):
        """Write SMS entry in HTML format."""
        try:
            # Extract sender information
            sender = self._extract_sender_info(soup, sms_info["phone_number"])

            # Write to conversation file with pre-extracted content
            self.conversation_manager.write_message_with_content(
                conversation_id,
                sms_info["message_content"],
                sms_info["attachments"],
                sms_info["timestamp"],
                sender,
            )

        except Exception as e:
            logger.error(f"Failed to write SMS HTML: {e}")

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
