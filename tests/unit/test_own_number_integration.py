"""
Integration tests for own_number extraction and usage in SMS processing.

Tests that the user's own phone number is correctly extracted from Phones.vcf
and used throughout the processing pipeline.

Following TDD: These tests are written to verify the integration works end-to-end.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sms import process_html_files_param, get_first_phone_number


class TestOwnNumberIntegration:
    """Test that own_number is extracted and used in processing."""

    def test_process_html_files_extracts_own_number_from_vcf(self):
        """Test that process_html_files_param extracts own_number from Phones.vcf."""
        # Create a temporary directory with Phones.vcf
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create Phones.vcf with user's number
            vcf_content = """BEGIN:VCARD
VERSION:3.0
item1.TEL:+13474106066
item1.X-ABLabel:Google Voice
END:VCARD"""
            phones_vcf = tmpdir_path / "Phones.vcf"
            phones_vcf.write_text(vcf_content)
            
            # Create Calls directory (required by process_html_files_param)
            calls_dir = tmpdir_path / "Calls"
            calls_dir.mkdir()
            
            # Create a simple test HTML file
            test_html = calls_dir / "Test - Text - 2024-01-01T12_00_00Z.html"
            test_html.write_text("""
            <html><body><div class="message">
            <cite class="sender vcard"><a class="tel" href="tel:+15551234567">Test</a></cite>
            <q>Test message</q>
            </div></body></html>
            """)
            
            # Mock managers
            mock_conv_manager = MagicMock()
            mock_phone_manager = MagicMock()
            mock_phone_manager.get_alias.return_value = None
            mock_phone_manager.is_filtered.return_value = False
            mock_phone_manager.should_filter_group_conversation.return_value = False
            
            # Mock config
            mock_config = MagicMock()
            mock_config.enable_date_filtering = False
            mock_config.enable_phone_filtering = False
            
            # Process files - this should extract own_number from Phones.vcf
            # We're checking that it doesn't crash and processes the file
            with patch('sms.logger') as mock_logger:
                stats = process_html_files_param(
                    processing_dir=tmpdir_path,
                    src_filename_map={},
                    conversation_manager=mock_conv_manager,
                    phone_lookup_manager=mock_phone_manager,
                    config=mock_config,
                    context=None,
                    limited_files=[test_html]
                )
            
            # Check that a log message about extracting own_number was made
            # This verifies the VCF was read and parsed
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            log_messages = ' '.join(log_calls)
            
            # Should have logged the extracted number
            assert "+13474106066" in log_messages or "own number" in log_messages.lower()

    def test_get_first_phone_number_skips_own_number_when_provided(self):
        """Test that get_first_phone_number properly skips own_number."""
        # HTML with only outgoing messages (user's number)
        html = """
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>
            <q>Test outgoing message</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # With own_number provided, should skip it and return 0 (no participant found)
        phone_number, participant = get_first_phone_number(
            messages, 
            fallback_number=0,
            own_number="+13474106066"
        )
        
        # Should return 0 because only number in messages is the user's own number
        assert phone_number == 0
        
    def test_get_first_phone_number_uses_fallback_when_only_own_number_present(self):
        """Test that fallback number is used when messages only contain own_number."""
        # HTML with only outgoing messages
        html = """
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">Me</a>
            </cite>
            <q>Outgoing message</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")
        
        # Provide Ed Harbur's number as fallback (from filename)
        ed_number = "+12034173178"
        
        # Should skip own_number and use fallback
        phone_number, participant = get_first_phone_number(
            messages,
            fallback_number=ed_number,
            own_number="+13474106066"
        )
        
        # Should return the fallback number (Ed's number from filename)
        assert phone_number == ed_number
        assert phone_number != "+13474106066"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

