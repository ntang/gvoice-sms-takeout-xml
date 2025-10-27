"""
Unit tests for HTML conversation parser.

This module tests HTML parsing functionality for conversation filtering post-processor.
Tests cover successful parsing, metadata extraction, message extraction, HTML entity
handling, error cases, and edge conditions.

Test Coverage:
- Successful conversation file parsing
- Metadata extraction (conversation ID, total messages, date range)
- Message extraction with all fields
- Timestamp parsing to Unix milliseconds
- HTML entity decoding (&#10; → \n)
- Attachment link extraction
- Error handling (missing files, malformed HTML, missing elements)
- Edge cases (empty conversations, invalid timestamps, missing cells)

Author: Claude Code
Date: 2025-10-26
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from core.html_conversation_parser import HTMLConversationParser


class TestSuccessfulParsing:
    """Test successful parsing of well-formed HTML conversation files."""

    def test_parse_simple_conversation(self, tmp_path):
        """Test parsing a simple conversation with one message."""
        parser = HTMLConversationParser()

        # Create test HTML file
        html_content = """<!DOCTYPE html>
<html>
<head><title>SMS Conversation</title></head>
<body>
    <div class='header'>
        <h1>SMS Conversation: +12025948401</h1>
        <p>Total Messages: 1</p>
        <p>Date Range: 2024-06-01</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-06-01 00:04:50</td>
                <td class="sender">Me</td>
                <td class="message">Stop</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test_conversation.html"
        test_file.write_text(html_content)

        # Parse file
        result = parser.parse_conversation_file(test_file)

        # Verify result
        assert result is not None
        assert result['conversation_id'] == '+12025948401'
        assert result['total_messages'] == 1
        assert result['date_range'] == '2024-06-01'
        assert len(result['messages']) == 1

        message = result['messages'][0]
        assert message['sender'] == 'Me'
        assert message['text'] == 'Stop'
        assert message['attachments'] == []
        assert isinstance(message['timestamp'], int)
        assert message['timestamp'] > 0

    def test_parse_multi_message_conversation(self, tmp_path):
        """Test parsing conversation with multiple messages."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Alice_Bob</h1>
        <p>Total Messages: 3</p>
        <p>Date Range: 2024-01-01 to 2024-01-02</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 10:00:00</td>
                <td class="sender">Me</td>
                <td class="message">Hello Alice</td>
                <td class="attachments"></td>
            </tr>
            <tr>
                <td class="timestamp">2024-01-01 10:05:00</td>
                <td class="sender">+15551234567</td>
                <td class="message">Hi Bob!</td>
                <td class="attachments"></td>
            </tr>
            <tr>
                <td class="timestamp">2024-01-02 08:30:00</td>
                <td class="sender">Me</td>
                <td class="message">See you later</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "multi_message.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert result['conversation_id'] == 'Alice_Bob'
        assert result['total_messages'] == 3
        assert len(result['messages']) == 3

        # Verify message order and senders
        assert result['messages'][0]['sender'] == 'Me'
        assert result['messages'][1]['sender'] == '+15551234567'
        assert result['messages'][2]['sender'] == 'Me'


class TestMetadataExtraction:
    """Test metadata extraction from HTML header."""

    def test_extract_conversation_id(self, tmp_path):
        """Test extraction of conversation ID from header."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Ed_Harbur_Phil_CSHC</h1>
        <p>Total Messages: 5</p>
        <p>Date Range: 2024-12-01</p>
    </div>
    <table><tbody></tbody></table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert result['conversation_id'] == 'Ed_Harbur_Phil_CSHC'

    def test_extract_total_messages(self, tmp_path):
        """Test extraction of total messages count."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: +1234567890</h1>
        <p>Total Messages: 42</p>
        <p>Date Range: 2024-01-01</p>
    </div>
    <table><tbody></tbody></table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert result['total_messages'] == 42

    def test_extract_date_range(self, tmp_path):
        """Test extraction of date range."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: +1234567890</h1>
        <p>Total Messages: 10</p>
        <p>Date Range: 2022-01-01 to 2024-12-31</p>
    </div>
    <table><tbody></tbody></table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert result['date_range'] == '2022-01-01 to 2024-12-31'


class TestMessageExtraction:
    """Test message extraction from HTML table."""

    def test_extract_message_fields(self, tmp_path):
        """Test that all message fields are extracted correctly."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-06-15 14:30:45</td>
                <td class="sender">+15551234567</td>
                <td class="message">Hello world</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert len(result['messages']) == 1

        msg = result['messages'][0]
        assert 'timestamp' in msg
        assert 'sender' in msg
        assert 'text' in msg
        assert 'attachments' in msg
        assert msg['sender'] == '+15551234567'
        assert msg['text'] == 'Hello world'

    def test_parse_timestamp_to_unix_ms(self, tmp_path):
        """Test timestamp parsing converts to Unix milliseconds."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
                <td class="message">Test</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        msg = result['messages'][0]

        # Verify it's a valid Unix timestamp in milliseconds
        assert isinstance(msg['timestamp'], int)
        assert msg['timestamp'] > 1000000000000  # After year 2001 in ms
        assert msg['timestamp'] < 2000000000000  # Before year 2033 in ms

    def test_handle_html_entities_in_message(self, tmp_path):
        """Test HTML entity decoding (&#10; → newline)."""
        parser = HTMLConversationParser()

        # HTML with encoded newline (&#10; is newline entity)
        # Note: We write the HTML with &#10; directly (not &amp;#10;)
        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
                <td class="message">Line 1&#10;Line 2&#10;Line 3</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content, encoding='utf-8')

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        msg = result['messages'][0]

        # Should decode &#10; to actual newline
        assert '\n' in msg['text']
        assert 'Line 1\nLine 2\nLine 3' in msg['text']


class TestAttachmentExtraction:
    """Test attachment link extraction."""

    def test_extract_single_attachment(self, tmp_path):
        """Test extraction of single attachment link."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
                <td class="message">Check this out</td>
                <td class="attachments">
                    <a href="attachments/image1.jpg" class="attachment">image1.jpg</a>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        msg = result['messages'][0]
        assert len(msg['attachments']) == 1
        assert msg['attachments'][0] == 'attachments/image1.jpg'

    def test_extract_multiple_attachments(self, tmp_path):
        """Test extraction of multiple attachment links."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
                <td class="message">Photos from trip</td>
                <td class="attachments">
                    <a href="attachments/photo1.jpg" class="attachment">photo1.jpg</a>
                    <a href="attachments/photo2.jpg" class="attachment">photo2.jpg</a>
                    <a href="attachments/photo3.jpg" class="attachment">photo3.jpg</a>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        msg = result['messages'][0]
        assert len(msg['attachments']) == 3
        assert 'attachments/photo1.jpg' in msg['attachments']
        assert 'attachments/photo2.jpg' in msg['attachments']
        assert 'attachments/photo3.jpg' in msg['attachments']


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_file_not_found(self, tmp_path):
        """Test handling of non-existent file."""
        parser = HTMLConversationParser()

        non_existent_file = tmp_path / "does_not_exist.html"
        result = parser.parse_conversation_file(non_existent_file)

        assert result is None

    def test_missing_header_div(self, tmp_path):
        """Test handling of HTML without header div."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
                <td class="message">Test</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        # Should fail without header
        assert result is None

    def test_missing_h1_in_header(self, tmp_path):
        """Test handling of header without h1 title."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <p>Total Messages: 1</p>
    </div>
    <table><tbody></tbody></table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is None

    def test_missing_table(self, tmp_path):
        """Test handling of HTML without table (no messages)."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 0</p>
    </div>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        # Should succeed but have empty messages list
        assert result is not None
        assert len(result['messages']) == 0

    def test_table_without_tbody(self, tmp_path):
        """Test handling of table without tbody element."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tr>
            <td class="timestamp">2024-01-01 12:00:00</td>
            <td class="sender">Me</td>
            <td class="message">Test</td>
            <td class="attachments"></td>
        </tr>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        # Parser expects tbody, so this should have no messages
        assert result is not None
        assert len(result['messages']) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_conversation(self, tmp_path):
        """Test conversation with no messages."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Empty</h1>
        <p>Total Messages: 0</p>
        <p>Date Range: N/A</p>
    </div>
    <table>
        <tbody></tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert result['conversation_id'] == 'Empty'
        assert result['total_messages'] == 0
        assert len(result['messages']) == 0

    def test_row_with_missing_cells(self, tmp_path):
        """Test handling of row with < 4 cells."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 2</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
            </tr>
            <tr>
                <td class="timestamp">2024-01-01 12:05:00</td>
                <td class="sender">Me</td>
                <td class="message">Valid message</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        # Should skip malformed row, parse valid row
        assert result is not None
        assert len(result['messages']) == 1
        assert result['messages'][0]['text'] == 'Valid message'

    def test_invalid_timestamp_format(self, tmp_path):
        """Test handling of invalid timestamp format."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">Invalid Date Format</td>
                <td class="sender">Me</td>
                <td class="message">Test</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        # Should still parse but with timestamp=0
        assert result is not None
        assert len(result['messages']) == 1
        assert result['messages'][0]['timestamp'] == 0

    def test_empty_message_text(self, tmp_path):
        """Test handling of empty message text."""
        parser = HTMLConversationParser()

        html_content = """<!DOCTYPE html>
<html>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test</h1>
        <p>Total Messages: 1</p>
    </div>
    <table>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 12:00:00</td>
                <td class="sender">Me</td>
                <td class="message"></td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        test_file = tmp_path / "test.html"
        test_file.write_text(html_content)

        result = parser.parse_conversation_file(test_file)

        assert result is not None
        assert len(result['messages']) == 1
        assert result['messages'][0]['text'] == ''
