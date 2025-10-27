"""
HTML conversation parser for post-processing.

This module parses generated HTML conversation files to extract structured
message data for filtering and analysis. It handles the HTML format generated
by the conversation manager and provides clean message extraction.

HTML Structure:
- Header div with metadata (total messages, date range)
- Table with message rows (timestamp, sender, message, attachments)
- CSS classes: timestamp, sender, message, attachments
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import html

logger = logging.getLogger(__name__)


class HTMLConversationParser:
    """
    Parses HTML conversation files to extract message data.

    Example HTML structure:
        <div class='header'>
            <h1>SMS Conversation: +12025948401</h1>
            <p>Total Messages: 1</p>
            <p>Date Range: 2024-06-01</p>
        </div>
        <table>
            <tr>
                <td class="timestamp">2024-06-01 00:04:50</td>
                <td class="sender">Me</td>
                <td class="message">Stop</td>
                <td class="attachments"></td>
            </tr>
        </table>
    """

    def __init__(self):
        """Initialize HTML conversation parser."""
        pass

    def parse_conversation_file(
        self,
        file_path: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Parse HTML conversation file.

        Args:
            file_path: Path to HTML conversation file

        Returns:
            Dictionary with conversation data:
            {
                'conversation_id': '+12025948401',
                'total_messages': 1,
                'date_range': '2024-06-01',
                'messages': [
                    {
                        'timestamp': 1717200290000,  # Unix ms
                        'sender': 'Me',
                        'text': 'Stop',
                        'attachments': []
                    }
                ]
            }

            Returns None if parsing fails.

        Example:
            parser = HTMLConversationParser()
            data = parser.parse_conversation_file(Path("conversations/+1234567890.html"))
            print(f"Conversation has {len(data['messages'])} messages")
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            html_content = file_path.read_text(encoding='utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract metadata from header
            metadata = self._extract_metadata(soup)
            if not metadata:
                logger.error(f"Failed to extract metadata from {file_path.name}")
                return None

            # Extract messages from table
            messages = self._extract_messages(soup)

            return {
                'conversation_id': metadata['conversation_id'],
                'total_messages': metadata['total_messages'],
                'date_range': metadata['date_range'],
                'file_path': str(file_path),
                'messages': messages
            }

        except Exception as e:
            logger.error(f"Error parsing {file_path.name}: {e}", exc_info=True)
            return None

    def _extract_metadata(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from HTML header.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Dictionary with metadata:
            {
                'conversation_id': '+12025948401',
                'total_messages': 1,
                'date_range': '2024-06-01'
            }

            Returns None if extraction fails.
        """
        try:
            header = soup.find('div', class_='header')
            if not header:
                logger.error("No header div found in HTML")
                return None

            # Extract conversation ID from h1 title
            h1 = header.find('h1')
            if not h1:
                logger.error("No h1 title found in header")
                return None

            # Parse: "SMS Conversation: +12025948401"
            title_text = h1.get_text(strip=True)
            match = re.search(r'SMS Conversation:\s*(.+)', title_text)
            if not match:
                logger.error(f"Could not parse conversation ID from title: {title_text}")
                return None

            conversation_id = match.group(1).strip()

            # Extract total messages
            total_messages = 0
            for p in header.find_all('p'):
                text = p.get_text(strip=True)
                match = re.match(r'Total Messages:\s*(\d+)', text)
                if match:
                    total_messages = int(match.group(1))
                    break

            # Extract date range
            date_range = ""
            for p in header.find_all('p'):
                text = p.get_text(strip=True)
                if text.startswith('Date Range:'):
                    date_range = text.replace('Date Range:', '').strip()
                    break

            return {
                'conversation_id': conversation_id,
                'total_messages': total_messages,
                'date_range': date_range
            }

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}", exc_info=True)
            return None

    def _extract_messages(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract messages from HTML table.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of message dictionaries:
            [
                {
                    'timestamp': 1717200290000,  # Unix ms
                    'sender': 'Me',
                    'text': 'Stop',
                    'attachments': []
                }
            ]
        """
        messages = []

        try:
            table = soup.find('table')
            if not table:
                logger.warning("No table found in HTML")
                return messages

            tbody = table.find('tbody')
            if not tbody:
                logger.warning("No tbody found in table")
                return messages

            rows = tbody.find_all('tr')
            for row in rows:
                message = self._parse_message_row(row)
                if message:
                    messages.append(message)

        except Exception as e:
            logger.error(f"Error extracting messages: {e}", exc_info=True)

        return messages

    def _parse_message_row(self, row) -> Optional[Dict[str, Any]]:
        """
        Parse a single message row from HTML table.

        Args:
            row: BeautifulSoup <tr> element

        Returns:
            Message dictionary or None if parsing fails:
            {
                'timestamp': 1717200290000,
                'sender': 'Me',
                'text': 'Stop',
                'attachments': []
            }
        """
        try:
            cells = row.find_all('td')
            if len(cells) < 4:
                logger.warning(f"Row has {len(cells)} cells, expected 4")
                return None

            # Extract timestamp
            timestamp_text = cells[0].get_text(strip=True)
            timestamp_ms = self._parse_timestamp(timestamp_text)

            # Extract sender
            sender = cells[1].get_text(strip=True)

            # Extract message text (handle HTML entities)
            message_html = str(cells[2])
            message_text = self._extract_message_text(cells[2])

            # Extract attachments
            attachments = self._extract_attachments(cells[3])

            return {
                'timestamp': timestamp_ms,
                'sender': sender,
                'text': message_text,
                'attachments': attachments
            }

        except Exception as e:
            logger.warning(f"Error parsing message row: {e}")
            return None

    def _parse_timestamp(self, timestamp_text: str) -> int:
        """
        Parse timestamp string to Unix milliseconds.

        Args:
            timestamp_text: Timestamp string like "2024-06-01 00:04:50"

        Returns:
            Unix timestamp in milliseconds

        Example:
            >>> parser._parse_timestamp("2024-06-01 00:04:50")
            1717200290000
        """
        try:
            # Parse: "2024-06-01 00:04:50"
            dt = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp() * 1000)
        except ValueError as e:
            logger.warning(f"Could not parse timestamp '{timestamp_text}': {e}")
            return 0

    def _extract_message_text(self, cell) -> str:
        """
        Extract message text from cell, handling HTML entities.

        Args:
            cell: BeautifulSoup <td> element

        Returns:
            Decoded message text

        Example:
            Input: "Please use the link&amp;#10;https://example.com"
            Output: "Please use the link\nhttps://example.com"
        """
        # Get raw HTML content
        cell_html = str(cell)

        # Extract text between <td> tags
        match = re.search(r'<td[^>]*class="message"[^>]*>(.*?)</td>', cell_html, re.DOTALL)
        if not match:
            return cell.get_text(strip=True)

        message_html = match.group(1)

        # Decode HTML entities (&amp;#10; -> &#10; -> \n)
        decoded = html.unescape(message_html)

        # Remove any remaining HTML tags
        decoded = re.sub(r'<[^>]+>', '', decoded)

        return decoded.strip()

    def _extract_attachments(self, cell) -> List[str]:
        """
        Extract attachment links from cell.

        Args:
            cell: BeautifulSoup <td> element

        Returns:
            List of attachment URLs

        Example:
            <td class="attachments">
                <a href="attachments/image1.jpg">image1.jpg</a>
                <a href="attachments/image2.jpg">image2.jpg</a>
            </td>
            Returns: ['attachments/image1.jpg', 'attachments/image2.jpg']
        """
        attachments = []

        try:
            links = cell.find_all('a', class_='attachment')
            for link in links:
                href = link.get('href')
                if href:
                    attachments.append(href)
        except Exception as e:
            logger.warning(f"Error extracting attachments: {e}")

        return attachments

    def parse_batch(
        self,
        file_paths: List[Path],
        skip_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple conversation files.

        Args:
            file_paths: List of HTML file paths
            skip_on_error: If True, skip files with parse errors
                          If False, stop on first error

        Returns:
            List of parsed conversation data

        Example:
            parser = HTMLConversationParser()
            conversations = parser.parse_batch([
                Path("conversations/+1234567890.html"),
                Path("conversations/+0987654321.html")
            ])
            print(f"Parsed {len(conversations)} conversations")
        """
        results = []

        for file_path in file_paths:
            try:
                data = self.parse_conversation_file(file_path)
                if data:
                    results.append(data)
                elif not skip_on_error:
                    logger.error(f"Failed to parse {file_path.name}, stopping batch")
                    break
            except Exception as e:
                logger.error(f"Error parsing {file_path.name}: {e}", exc_info=True)
                if not skip_on_error:
                    break

        logger.info(f"Parsed {len(results)}/{len(file_paths)} conversation files")
        return results

    def get_conversation_id_from_filename(self, file_path: Path) -> str:
        """
        Extract conversation ID from filename.

        Args:
            file_path: Path to HTML file

        Returns:
            Conversation ID (phone number or name)

        Example:
            >>> parser.get_conversation_id_from_filename(Path("+12025948401.html"))
            '+12025948401'
        """
        # Remove .html extension
        filename = file_path.stem

        # Handle .archived extension
        if filename.endswith('.archived'):
            filename = filename[:-9]  # Remove '.archived'

        return filename
