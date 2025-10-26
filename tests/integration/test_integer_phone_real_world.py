"""
Integration test for real-world integer phone number scenario.

Simulates processing a file like "+17326389287 - Text - 2024-09-26T19_33_21Z.html"
containing only outgoing messages where phone number extraction returns integer.

Bug #26: Prevents 'object of type int has no len()' TypeError in production scenario
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bs4 import BeautifulSoup
from core.processing_config import ProcessingConfig
from core.filtering_service import FilteringService
from sms import should_skip_message_by_phone_param, write_sms_messages


class TestRealWorldIntegerPhoneProcessing:
    """Test real-world scenario where integer phone numbers cause len() error."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create config with filtering enabled (the scenario that triggers the bug)
        self.config = Mock(spec=ProcessingConfig)
        self.config.filter_non_phone_numbers = True
        self.config.filter_numbers_without_aliases = False
        self.config.include_service_codes = False
        self.config.exclude_older_than = None
        self.config.exclude_newer_than = None
        self.config.include_date_range = None

        # Create mock managers
        self.phone_lookup_manager = MagicMock()
        self.phone_lookup_manager.has_alias.return_value = True
        self.phone_lookup_manager.is_excluded.return_value = False
        self.phone_lookup_manager.get_alias.return_value = "Test Contact"

        self.conversation_manager = MagicMock()
        self.conversation_manager.get_conversation_id.return_value = "Test_Contact"

    def test_process_file_with_integer_fallback_number(self):
        """
        Test processing file where fallback number is integer.

        Scenario:
        - File: +17326389287 - Text - 2024-09-26T19_33_21Z.html
        - Contains only outgoing messages (all from "Me")
        - get_first_phone_number() returns (0, ...) because all senders are "Me"
        - search_fallback_numbers() returns 17326389287 (int) from filename
        - phone_number is now int, passed to filtering function
        - BEFORE FIX: Crashes with "object of type 'int' has no len()"
        - AFTER FIX: Should handle gracefully
        """
        # Simulate the exact data flow:
        # 1. extract_fallback_number() returns int
        fallback_number = 17326389287  # int, not str

        # 2. This int gets used as phone_number
        phone_number = fallback_number

        # 3. Phone number (int) passed to filtering function
        # This is the line that crashes before the fix
        try:
            result = should_skip_message_by_phone_param(
                phone_number,  # This is an int!
                self.phone_lookup_manager,
                self.config
            )
            # If we get here without exception, the test passes
            assert isinstance(result, bool), "Should return boolean"

        except TypeError as e:
            if "has no len()" in str(e):
                pytest.fail(f"TypeError with len() - bug not fixed: {e}")
            else:
                raise

    def test_filtering_service_with_integer_input(self):
        """Test FilteringService directly with integer input."""
        filtering_service = FilteringService(self.config)

        # Test with various integer inputs that occur in real processing
        test_cases = [
            (0, "Zero from no participant found"),
            (22395, "Short code from filename"),
            (17326389287, "Full number from fallback"),
            (8003092350, "Toll-free number"),
        ]

        for phone_number, description in test_cases:
            try:
                # This should not crash
                result = filtering_service.should_skip_by_phone(
                    phone_number,
                    self.phone_lookup_manager
                )
                assert isinstance(result, bool), f"Failed for {description}"

            except TypeError as e:
                if "has no len()" in str(e):
                    pytest.fail(f"TypeError for {description}: {e}")
                else:
                    raise

    def test_write_sms_messages_with_integer_phone_number(self):
        """
        Test write_sms_messages() function with integer phone number.

        This is the high-level function that was failing in production.
        """
        # Create minimal mock HTML message
        html = """
        <div class="message">
            <cite class="sender vcard">
                <a class="tel" href="tel:+13474106066">
                    <abbr class="fn" title="">Me</abbr>
                </a>
            </cite>
            <q>Test message</q>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="message")

        # Mock parameters
        file = "+17326389287 - Text - 2024-09-26T19_33_21Z.html"
        own_number = "+13474106066"
        src_filename_map = {}

        # The function should process without crashing
        # Even though phone extraction returns int and filtering is applied
        try:
            write_sms_messages(
                file=file,
                messages_raw=messages,
                own_number=own_number,
                src_filename_map=src_filename_map,
                conversation_manager=self.conversation_manager,
                phone_lookup_manager=self.phone_lookup_manager,
                page_participants_raw=None,
                soup=soup,
                config=self.config,
                context=None
            )
            # If we get here, test passes (no crash)
            assert True, "Processing completed without crash"

        except TypeError as e:
            if "has no len()" in str(e):
                pytest.fail(f"write_sms_messages crashed with len() error: {e}")
            else:
                # Re-raise if it's a different TypeError
                raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
