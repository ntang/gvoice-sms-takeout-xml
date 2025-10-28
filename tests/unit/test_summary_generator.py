"""
Unit tests for AI summary generation using Gemini CLI.

This module tests the SummaryGenerator class that extracts messages
from conversation HTML files and generates summaries using Gemini CLI.
"""

import pytest
import subprocess
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from core.summary_generator import SummaryGenerator


class TestSummaryGenerator:
    """Test suite for SummaryGenerator class."""

    def test_gemini_cli_available(self):
        """Test 1: Verify gemini CLI is available on system."""
        # This test should pass on systems with gemini installed
        result = subprocess.run(
            ['which', 'gemini'],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, "gemini command not found - install from https://ai.google.dev/gemini-api/docs/cli"
        assert '/gemini' in result.stdout, "gemini path should be returned"

    def test_extract_messages_from_html(self, tmp_path):
        """Test 2: Parse conversation HTML TABLE structure correctly."""
        # Create test HTML with TABLE structure (matches actual conversation format)
        html_content = """<!DOCTYPE html>
<html lang='en'>
<head><title>Test Conversation</title></head>
<body>
    <div class='header'>
        <h1>SMS Conversation: Test_User</h1>
        <p>Total Messages: 3</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>Sender</th>
                <th>Message</th>
                <th>Attachments</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="timestamp">2024-01-01 10:00:00</td>
                <td class="sender">Alice</td>
                <td class="message">Hello, how are you?</td>
                <td class="attachments"></td>
            </tr>
            <tr>
                <td class="timestamp">2024-01-01 10:01:30</td>
                <td class="sender">Bob</td>
                <td class="message">I'm good, thanks!</td>
                <td class="attachments"></td>
            </tr>
            <tr>
                <td class="timestamp">2024-01-01 10:05:15</td>
                <td class="sender">Alice</td>
                <td class="message">📞 Outgoing call to Bob (Duration: 05:23)</td>
                <td class="attachments"></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

        # Write to temp file
        test_file = tmp_path / "test_conversation.html"
        test_file.write_text(html_content, encoding='utf-8')

        # Mock the verify method to skip CLI check
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Extract messages
        messages = generator.extract_messages_from_html(test_file)

        # Verify
        assert len(messages) == 3, "Should extract 3 messages"

        # Check first message
        assert messages[0]['timestamp'] == '2024-01-01 10:00:00'
        assert messages[0]['sender'] == 'Alice'
        assert messages[0]['text'] == 'Hello, how are you?'
        assert messages[0]['type'] == 'sms'

        # Check call message
        assert messages[2]['type'] == 'call', "Should detect call by 📞 emoji"
        assert 'Outgoing call' in messages[2]['text']

    def test_build_gemini_prompt(self):
        """Test 3: Build proper prompt with message content."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        messages = [
            {'timestamp': '2024-01-01 10:00:00', 'sender': 'Alice', 'text': 'Hello'},
            {'timestamp': '2024-01-01 10:01:00', 'sender': 'Bob', 'text': 'Hi'},
            {'timestamp': '2024-01-02 15:30:00', 'sender': 'Alice', 'text': 'How are you?'},
        ]

        prompt = generator.build_gemini_prompt(messages, "Test_Conversation")

        # Verify prompt structure
        assert 'Test_Conversation' in prompt, "Should include conversation ID"
        assert 'Alice: Hello' in prompt, "Should include message content"
        assert 'Bob: Hi' in prompt, "Should include all messages"
        assert '3 messages' in prompt, "Should mention message count"
        assert '2024-01-01 to 2024-01-02' in prompt, "Should include date range"
        assert 'comprehensive paragraph' in prompt, "Should have instructions"

    @patch('subprocess.run')
    def test_generate_summary_success(self, mock_run):
        """Test 4: Mock successful Gemini CLI call."""
        # Mock successful Gemini response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "This is a professional conversation between Alice and Bob discussing project details. The conversation spans two days and includes multiple check-ins. They successfully coordinated meeting times and deliverables."
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Create test file
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<table><tbody>
                <tr><td>2024-01-01 10:00</td><td>Alice</td><td>Hello</td><td></td></tr>
            </tbody></table>""")
            test_file = Path(f.name)

        try:
            result = generator.generate_summary(test_file)

            # Verify
            assert result is not None, "Should return result"
            assert 'summary' in result, "Should have summary key"
            assert len(result['summary']) > 20, "Summary should be substantial"
            assert 'generated_at' in result, "Should have timestamp"
            assert 'message_count' in result, "Should have message count"
            assert 'date_range' in result, "Should have date range"
        finally:
            test_file.unlink()

    @patch('subprocess.run')
    def test_generate_summary_failure(self, mock_run):
        """Test 5: Handle Gemini CLI non-zero exit codes."""
        # Mock failed Gemini call
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: Invalid API key"
        mock_run.return_value = mock_result

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<table><tbody>
                <tr><td>2024-01-01 10:00</td><td>Alice</td><td>Hello</td><td></td></tr>
            </tbody></table>""")
            test_file = Path(f.name)

        try:
            result = generator.generate_summary(test_file)

            # Should return None on failure
            assert result is None, "Should return None on CLI failure"
        finally:
            test_file.unlink()

    @patch('subprocess.run')
    def test_gemini_timeout_handling(self, mock_run):
        """Test 6: Mock subprocess taking >60s and verify timeout."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired('gemini', 60)

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator(timeout=60)

        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<table><tbody>
                <tr><td>2024-01-01 10:00</td><td>Alice</td><td>Hello</td><td></td></tr>
            </tbody></table>""")
            test_file = Path(f.name)

        try:
            result = generator.generate_summary(test_file)

            # Should handle timeout gracefully
            assert result is None, "Should return None on timeout"
        finally:
            test_file.unlink()

    @patch('subprocess.run')
    def test_gemini_malformed_output(self, mock_run):
        """Test 7: Gemini returns empty/gibberish, verify handled gracefully."""
        # Test various malformed outputs
        test_cases = [
            "",  # Empty
            "   ",  # Whitespace only
            "abc",  # Too short (< 20 chars)
            "I cannot help with that request.",  # Refusal
            "As an AI, I can't provide that information.",  # Refusal
        ]

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<table><tbody>
                <tr><td>2024-01-01 10:00</td><td>Alice</td><td>Hello</td><td></td></tr>
            </tbody></table>""")
            test_file = Path(f.name)

        try:
            for bad_output in test_cases:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = bad_output
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                result = generator.generate_summary(test_file)

                assert result is None, f"Should reject malformed output: '{bad_output}'"
        finally:
            test_file.unlink()

    def test_save_summaries_json(self, tmp_path):
        """Test 8: Write correct JSON structure."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        summaries = {
            'Alice_Bob': {
                'summary': 'This is a test summary about Alice and Bob.',
                'generated_at': '2024-01-01T12:00:00',
                'message_count': 10,
                'date_range': '2024-01-01 to 2024-01-05',
                'model': 'gemini-2.5-pro'
            },
            'Carol_Dave': {
                'summary': 'This is another test summary.',
                'generated_at': '2024-01-02T14:30:00',
                'message_count': 5,
                'date_range': '2024-01-02 to 2024-01-03',
                'model': 'gemini-2.5-pro'
            }
        }

        output_file = tmp_path / "summaries.json"
        generator.save_summaries(summaries, output_file)

        # Verify file was created
        assert output_file.exists(), "JSON file should be created"

        # Load and verify structure
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'version' in data, "Should have version"
        assert data['version'] == '1.1', "Version should be 1.1 with model tracking"
        assert 'generated_at' in data, "Should have generation timestamp"
        assert 'generated_by' in data, "Should have generator info"
        assert 'Gemini CLI' in data['generated_by']
        assert 'stats' in data, "Should have stats"
        assert data['stats']['total_conversations'] == 2
        assert 'model_usage' in data, "Should have model_usage section"
        assert 'summaries' in data, "Should have summaries"
        assert 'Alice_Bob' in data['summaries']

    def test_load_existing_summaries(self, tmp_path):
        """Test 9: Load and merge with existing summaries."""
        # Create existing summaries file
        existing_data = {
            'version': '1.0',
            'generated_at': '2024-01-01T10:00:00',
            'generated_by': 'Gemini CLI',
            'stats': {'total_conversations': 1},
            'summaries': {
                'Existing_Conv': {
                    'summary': 'Existing summary',
                    'generated_at': '2024-01-01T10:00:00',
                    'message_count': 5,
                    'date_range': '2024-01-01 to 2024-01-02'
                }
            }
        }

        json_file = tmp_path / "summaries.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Load summaries
        summaries = generator.load_summaries(json_file)

        # Verify
        assert len(summaries) == 1, "Should load existing summaries"
        assert 'Existing_Conv' in summaries
        assert summaries['Existing_Conv']['summary'] == 'Existing summary'

    def test_skip_archived_conversations(self, tmp_path):
        """Test 10: Only process non-.archived.html files."""
        # Create test files
        normal_file = tmp_path / "conversation.html"
        archived_file = tmp_path / "old.archived.html"
        index_file = tmp_path / "index.html"

        for f in [normal_file, archived_file, index_file]:
            f.write_text("<table><tbody><tr><td>2024-01-01</td><td>Test</td><td>Hi</td><td></td></tr></tbody></table>")

        # Get all HTML files
        all_files = list(tmp_path.glob('*.html'))
        assert len(all_files) == 3, "Should have 3 HTML files"

        # Filter like the CLI command does
        non_archived = [
            f for f in all_files
            if not f.name.endswith('.archived.html') and f.name != 'index.html'
        ]

        # Verify filtering
        assert len(non_archived) == 1, "Should have 1 non-archived file"
        assert non_archived[0].name == 'conversation.html'

    def test_calculate_date_range(self):
        """Test 11: Extract correct date range from messages."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Test with messages spanning multiple days
        messages = [
            {'timestamp': '2024-01-15 10:00:00', 'sender': 'Alice', 'text': 'Hi'},
            {'timestamp': '2024-01-15 14:30:00', 'sender': 'Bob', 'text': 'Hello'},
            {'timestamp': '2024-01-20 09:00:00', 'sender': 'Alice', 'text': 'Follow up'},
        ]

        date_range = generator._calculate_date_range(messages)

        assert date_range == '2024-01-15 to 2024-01-20', "Should calculate correct date range"

        # Test with empty messages
        assert generator._calculate_date_range([]) == 'Unknown'

        # Test with single day
        single_day = [
            {'timestamp': '2024-01-15 10:00:00', 'sender': 'Alice', 'text': 'Hi'},
            {'timestamp': '2024-01-15 14:00:00', 'sender': 'Bob', 'text': 'Bye'},
        ]
        date_range = generator._calculate_date_range(single_day)
        assert date_range == '2024-01-15 to 2024-01-15', "Should handle single day"

    def test_full_conversation_no_sampling(self):
        """Test 12: Verify ALL messages included in prompt (no sampling)."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Create 200 messages to test that ALL are included (not sampled)
        messages = []
        for i in range(200):
            messages.append({
                'timestamp': f'2024-01-01 {i % 24:02d}:{i % 60:02d}:00',
                'sender': 'Alice' if i % 2 == 0 else 'Bob',
                'text': f'Message number {i}'
            })

        prompt = generator.build_gemini_prompt(messages, "Large_Conversation")

        # Verify ALL messages are included (not sampled)
        assert 'showing all 200 messages' in prompt, "Should say 'showing all 200 messages'"
        assert 'first 25 and last 25' not in prompt, "Should NOT mention sampling"

        # Verify messages from beginning, middle, and end are all present
        assert 'Message number 0' in prompt, "Should include first message"
        assert 'Message number 100' in prompt, "Should include middle message (would be missing if sampled)"
        assert 'Message number 199' in prompt, "Should include last message"

        # Count how many messages are actually in the prompt
        # Each message should appear as "Sender: Message number X"
        message_count = sum(1 for i in range(200) if f'Message number {i}' in prompt)
        assert message_count == 200, f"Should include all 200 messages, but only found {message_count}"

    def test_adaptive_timeout_calculation(self):
        """Test 13: Verify timeout scales based on conversation size."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Test timeout calculation for different conversation sizes
        # Expected formula:
        # - Small (1-100 messages): 120s (2 min)
        # - Medium (101-500 messages): 300s (5 min)
        # - Large (501-1000 messages): 600s (10 min)
        # - Mega (1000+ messages): 900s (15 min)

        assert generator.get_timeout_for_conversation(10) == 120, "Small conversation should get 2min timeout"
        assert generator.get_timeout_for_conversation(100) == 120, "Small conversation should get 2min timeout"
        assert generator.get_timeout_for_conversation(250) == 300, "Medium conversation should get 5min timeout"
        assert generator.get_timeout_for_conversation(750) == 600, "Large conversation should get 10min timeout"
        assert generator.get_timeout_for_conversation(1500) == 900, "Mega conversation should get 15min timeout"

    @patch('subprocess.run')
    def test_model_tracking_in_result(self, mock_run):
        """Test 14: Verify model field included in summary result."""
        # Mock successful Gemini response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "This is a professional conversation with comprehensive details."
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Create test file
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<table><tbody>
                <tr><td>2024-01-01 10:00</td><td>Alice</td><td>Hello there</td><td></td></tr>
            </tbody></table>""")
            test_file = Path(f.name)

        try:
            result = generator.generate_summary(test_file)

            # Verify model field is present
            assert result is not None, "Should return result"
            assert 'model' in result, "Should have 'model' field in result"
            assert result['model'] == 'gemini-2.5-pro', "Should track model as gemini-2.5-pro"
        finally:
            test_file.unlink()

    def test_json_includes_model_usage(self, tmp_path):
        """Test 15: Verify JSON output includes model_usage stats."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Create summaries with model tracking
        summaries = {
            'Conv1': {
                'summary': 'Summary 1',
                'generated_at': '2024-01-01T12:00:00',
                'message_count': 10,
                'date_range': '2024-01-01 to 2024-01-05',
                'model': 'gemini-2.5-pro'
            },
            'Conv2': {
                'summary': 'Summary 2',
                'generated_at': '2024-01-02T14:00:00',
                'message_count': 5,
                'date_range': '2024-01-02 to 2024-01-03',
                'model': 'gemini-2.5-pro'
            },
            'Conv3': {
                'summary': 'Summary 3',
                'generated_at': '2024-01-03T16:00:00',
                'message_count': 8,
                'date_range': '2024-01-03 to 2024-01-04',
                'model': 'gemini-2.0-flash-exp'
            }
        }

        output_file = tmp_path / "summaries.json"
        generator.save_summaries(summaries, output_file)

        # Load and verify structure
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Verify version bumped to 1.1
        assert data['version'] == '1.1', "Version should be 1.1 with model tracking"

        # Verify model_usage section exists
        assert 'model_usage' in data, "Should have model_usage section"
        assert 'gemini-2.5-pro' in data['model_usage'], "Should track Pro model usage"
        assert 'gemini-2.0-flash-exp' in data['model_usage'], "Should track Flash model usage"

        # Verify counts
        assert data['model_usage']['gemini-2.5-pro'] == 2, "Should count 2 Pro summaries"
        assert data['model_usage']['gemini-2.0-flash-exp'] == 1, "Should count 1 Flash summary"

    def test_quota_error_detection(self):
        """Test 16: Detect 429 quota errors in stderr."""
        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator()

        # Test quota error detection with real error format
        quota_stderr = '''Loaded cached credentials.
[{
  "error": {
    "code": 429,
    "message": "Quota exceeded for quota metric 'Gemini 2.5 Pro Requests' and limit 'Gemini 2.5"
  }
}]'''
        assert generator.is_quota_error(quota_stderr) == True, "Should detect 429 quota error"

        # Test non-quota 429 error
        other_429 = '{"error": {"code": 429, "message": "Too many requests"}}'
        assert generator.is_quota_error(other_429) == True, "Should detect any 429 error"

        # Test non-quota error
        other_stderr = '{"error": {"code": 500, "message": "Internal server error"}}'
        assert generator.is_quota_error(other_stderr) == False, "Should not detect non-429 errors"

        # Test empty stderr
        assert generator.is_quota_error('') == False, "Should not detect error in empty string"

    @patch('subprocess.run')
    def test_model_selection(self, mock_run):
        """Test 17: Verify correct model is passed to Gemini CLI."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "This is a comprehensive test summary with sufficient detail."
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch.object(SummaryGenerator, 'verify_gemini_available'):
            generator = SummaryGenerator(model='gemini-2.5-flash')

        # Create test file
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""<table><tbody>
                <tr><td>2024-01-01 10:00</td><td>Alice</td><td>Hello there friend</td><td></td></tr>
            </tbody></table>""")
            test_file = Path(f.name)

        try:
            result = generator.generate_summary(test_file, model='gemini-2.5-flash')

            # Verify command included -m flag with Flash model
            call_args = mock_run.call_args[0][0]
            assert '-m' in call_args, "Should include -m flag"
            flash_index = call_args.index('-m')
            assert call_args[flash_index + 1] == 'gemini-2.5-flash', "Should specify Flash model"

            # Verify result tracks Flash model
            assert result is not None, "Should return result"
            assert result['model'] == 'gemini-2.5-flash', "Should track Flash model in result"
        finally:
            test_file.unlink()
