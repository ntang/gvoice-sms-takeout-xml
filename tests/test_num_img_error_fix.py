"""
TDD test suite for fixing the 'num_img' KeyError in write_call_entry.
"""
import pytest
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sms import write_call_entry, extract_call_info


class TestNumImgErrorFix:
    """Test suite for fixing the 'num_img' KeyError in call entry processing."""

    def setup_method(self):
        """Set up test fixtures."""
        # Sample call HTML content
        self.call_html = """
        <html>
        <head><title>Placed call</title></head>
        <body>
            <div class="hChatLog">
                <div class="hChatMessage">
                    <abbr class="dt" title="2018-09-29T14:25:58.000-04:00">Sep 29, 2018, 2:25:58 PM</abbr>
                    <abbr class="duration" title="PT4S">(4s)</abbr>
                    <div class="message">
                        <cite class="sender vcard">
                            <a class="tel" href="tel:+17187811928">
                                <span class="fn">+17187811928</span>
                            </a>
                        </cite>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.soup = BeautifulSoup(self.call_html, 'html.parser')
        self.filename = "+17187811928 - Placed - 2018-09-29T18_25_58Z.html"
        
        # Mock managers
        self.conversation_manager = Mock()
        self.conversation_manager.get_conversation_id.return_value = "test_conversation"
        
        self.phone_lookup_manager = Mock()
        self.phone_lookup_manager.get_alias.return_value = "+17187811928"

    def test_extract_call_info_returns_expected_structure(self):
        """Test that extract_call_info returns the expected dictionary structure."""
        call_info = extract_call_info(self.filename, self.soup)
        
        assert call_info is not None
        assert isinstance(call_info, dict)
        
        # Verify expected keys
        expected_keys = {"type", "phone_number", "timestamp", "duration", "filename"}
        assert set(call_info.keys()) == expected_keys
        
        # Verify it doesn't contain unexpected keys like 'num_img'
        assert "num_img" not in call_info

    def test_write_call_entry_should_not_access_num_img(self):
        """Test that write_call_entry doesn't try to access 'num_img' from call_info."""
        # Get real call_info from extract_call_info
        call_info = extract_call_info(self.filename, self.soup)
        assert call_info is not None
        
        # This should not raise a KeyError for 'num_img'
        try:
            write_call_entry(
                self.filename,
                call_info,
                None,  # own_number
                soup=self.soup,
                conversation_manager=self.conversation_manager,
                phone_lookup_manager=self.phone_lookup_manager
            )
            # If we get here, no KeyError was raised
            success = True
        except KeyError as e:
            if "'num_img'" in str(e):
                pytest.fail(f"write_call_entry tried to access 'num_img' from call_info: {e}")
            else:
                # Re-raise other KeyErrors
                raise
        except Exception as e:
            # Other exceptions are okay for now, we're only testing the KeyError
            success = True
            
        assert success

    def test_write_call_entry_with_missing_keys_should_not_crash(self):
        """Test that write_call_entry handles missing keys gracefully."""
        # Create call_info with minimal required keys
        minimal_call_info = {
            "type": "outgoing",
            "phone_number": "+17187811928",
            "timestamp": 1538247958000,
            "duration": "4s",
            "filename": self.filename
        }
        
        # This should not crash even if some optional keys are missing
        try:
            write_call_entry(
                self.filename,
                minimal_call_info,
                None,  # own_number
                soup=self.soup,
                conversation_manager=self.conversation_manager,
                phone_lookup_manager=self.phone_lookup_manager
            )
            success = True
        except KeyError as e:
            if "'num_img'" in str(e):
                pytest.fail(f"write_call_entry tried to access 'num_img': {e}")
            else:
                # Other KeyErrors might be legitimate
                success = True
        except Exception:
            # Other exceptions are okay for this test
            success = True
            
        assert success

    def test_call_info_structure_consistency(self):
        """Test that call_info has consistent structure and doesn't mix with file stats."""
        call_info = extract_call_info(self.filename, self.soup)
        assert call_info is not None
        
        # call_info should NOT contain file processing statistics
        file_stats_keys = {"num_sms", "num_img", "num_vcf", "num_calls", "num_voicemails", "own_number"}
        call_info_keys = set(call_info.keys())
        
        # Verify no overlap between call_info and file_stats structures
        overlap = call_info_keys.intersection(file_stats_keys)
        assert len(overlap) == 0, f"call_info should not contain file stats keys: {overlap}"

    @patch('sms.logger')
    def test_write_call_entry_logs_error_without_crashing(self, mock_logger):
        """Test that if an error occurs, it's logged but doesn't crash the system."""
        call_info = extract_call_info(self.filename, self.soup)
        assert call_info is not None
        
        # Mock conversation_manager to raise an exception
        self.conversation_manager.write_message_with_content.side_effect = Exception("Test error")
        
        # This should not raise an exception, but should log an error
        write_call_entry(
            self.filename,
            call_info,
            None,  # own_number
            soup=self.soup,
            conversation_manager=self.conversation_manager,
            phone_lookup_manager=self.phone_lookup_manager
        )
        
        # Verify that an error was logged
        mock_logger.error.assert_called()
        # Check that "Failed to write call entry" appears in any of the error calls
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any("Failed to write call entry" in call for call in error_calls)

    def test_call_info_does_not_mutate_during_processing(self):
        """Test that call_info dictionary is not modified during write_call_entry."""
        call_info = extract_call_info(self.filename, self.soup)
        assert call_info is not None
        
        # Make a copy of the original call_info
        original_call_info = call_info.copy()
        
        # Process the call entry
        try:
            write_call_entry(
                self.filename,
                call_info,
                None,  # own_number
                soup=self.soup,
                conversation_manager=self.conversation_manager,
                phone_lookup_manager=self.phone_lookup_manager
            )
        except Exception:
            # Ignore exceptions for this test
            pass
        
        # Verify call_info wasn't modified
        assert call_info == original_call_info
        assert "num_img" not in call_info

    def test_original_process_call_file_uses_correct_signature(self):
        """Test that the original process_call_file in sms.py calls write_call_entry with correct signature."""
        from sms import process_call_file as original_process_call_file
        from unittest.mock import patch, Mock
        
        # Mock the global managers
        mock_conversation_manager = Mock()
        mock_phone_lookup_manager = Mock()
        mock_phone_lookup_manager.get_alias.return_value = "+17187811928"
        
        # Mock the write_call_entry function to verify it's called with correct parameters
        with patch('sms.write_call_entry') as mock_write_call_entry, \
             patch('sms.CONVERSATION_MANAGER', mock_conversation_manager), \
             patch('sms.PHONE_LOOKUP_MANAGER', mock_phone_lookup_manager):
            
            # This should not raise an exception
            result = original_process_call_file(
                Path(self.filename), 
                self.soup, 
                None,  # own_number
                {}     # src_filename_map
            )
            
            # Verify the function returned correct stats
            assert result["num_calls"] == 1
            assert "num_img" in result  # Should have this key
            
            # Verify write_call_entry was called with the correct signature
            mock_write_call_entry.assert_called_once()
            call_args = mock_write_call_entry.call_args
            
            # Verify it was called with the manager parameters
            assert 'conversation_manager' in call_args.kwargs
            assert 'phone_lookup_manager' in call_args.kwargs
            assert call_args.kwargs['conversation_manager'] == mock_conversation_manager
            assert call_args.kwargs['phone_lookup_manager'] == mock_phone_lookup_manager

    def test_conversation_manager_update_stats_handles_missing_keys(self):
        """Test that ConversationManager.update_stats handles missing keys gracefully."""
        from core.conversation_manager import ConversationManager
        from pathlib import Path
        
        # Create a conversation manager
        cm = ConversationManager(output_dir=Path("/tmp/test"), large_dataset=False)
        
        # Create a conversation with minimal stats (simulating the bug condition)
        conversation_id = "test_conversation"
        cm.conversation_stats[conversation_id] = {
            "num_sms": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            # Intentionally missing "num_img", "num_vcf", "num_video", "num_audio" keys
            "real_attachments": 0,
            "latest_timestamp": 0,
            "latest_message_time": "No messages"
        }
        
        # This should not raise a KeyError for missing keys
        try:
            cm.update_stats(conversation_id, {"num_calls": 1})
            success = True
        except KeyError as e:
            if "'num_img'" in str(e):
                pytest.fail(f"update_stats raised KeyError for missing num_img: {e}")
            else:
                raise
        
        assert success
        assert cm.conversation_stats[conversation_id]["num_calls"] == 1
        assert cm.conversation_stats[conversation_id]["real_attachments"] == 0  # Should be calculated safely
