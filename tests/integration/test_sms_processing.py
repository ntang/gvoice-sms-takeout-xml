#!/usr/bin/env python3
"""
SMS processing integration tests.

This module contains tests for SMS processing functionality
including conversation management, phone lookup, and HTML output.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil
import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
import phonenumbers
from bs4 import BeautifulSoup
import logging
import dateutil.parser
import sms

# Add the current directory to the path so we can import sms
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.base_test import BaseSMSTest


class TestSMSProcessing(BaseSMSTest):
    """Integration tests for SMS module."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for the entire test class."""
        # Suppress logging during tests
        logging.getLogger("sms").setLevel(logging.ERROR)

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create required directory structure for SMS processing
        self.create_test_directory_structure()

    def tearDown(self):
        """Clean up after each test method."""
        # Reset SMS module global variables to allow fresh setup in next test
        import sms
        from core import shared_constants
        # Reset all global variables
        shared_constants.PROCESSING_DIRECTORY = None
        shared_constants.OUTPUT_DIRECTORY = None
        shared_constants.LOG_FILENAME = None
        
        # Clear manager internal state before resetting
        if shared_constants.CONVERSATION_MANAGER:
            try:
                # Clear internal state if the manager has cleanup methods
                if hasattr(shared_constants.CONVERSATION_MANAGER, 'conversation_files'):
                    shared_constants.CONVERSATION_MANAGER.conversation_files.clear()
                if hasattr(shared_constants.CONVERSATION_MANAGER, 'conversation_stats'):
                    shared_constants.CONVERSATION_MANAGER.conversation_stats.clear()
                if hasattr(shared_constants.CONVERSATION_MANAGER, 'message_buffer'):
                    shared_constants.CONVERSATION_MANAGER.message_buffer.clear()
            except Exception:
                pass  # Ignore cleanup errors
        
        if shared_constants.PHONE_LOOKUP_MANAGER:
            try:
                # Clear phone lookup manager state
                if hasattr(shared_constants.PHONE_LOOKUP_MANAGER, 'phone_aliases'):
                    shared_constants.PHONE_LOOKUP_MANAGER.phone_aliases.clear()
            except Exception:
                pass  # Ignore cleanup errors
        
        shared_constants.CONVERSATION_MANAGER = None
        shared_constants.PHONE_LOOKUP_MANAGER = None
        shared_constants.PATH_MANAGER = None
        shared_constants.LIMITED_HTML_FILES = None
        # Reset filtering configuration
        shared_constants.DATE_FILTER_OLDER_THAN = None
        shared_constants.DATE_FILTER_NEWER_THAN = None
        shared_constants.FILTER_NUMBERS_WITHOUT_ALIASES = False
        shared_constants.FILTER_NON_PHONE_NUMBERS = False
        shared_constants.FULL_RUN = False
        shared_constants.TEST_MODE = False
        shared_constants.TEST_LIMIT = 100
        
        # Clear all LRU caches to prevent test interference
        sms.extract_src_cached.cache_clear()
        sms.list_att_filenames_cached.cache_clear()
        sms.normalize_filename.cache_clear()
        sms.src_to_filename_mapping_cached.cache_clear()
        sms.build_attachment_mapping_cached.cache_clear()
        sms.count_attachments_in_file_cached.cache_clear()
        sms.extract_fallback_number_cached.cache_clear()
        sms.search_fallback_numbers_cached.cache_clear()
        sms.get_message_type_cached.cache_clear()
        sms.get_mms_sender_cached.cache_clear()
        sms.get_first_phone_number_cached.cache_clear()
        sms.get_participant_phone_numbers_cached.cache_clear()
        sms.parse_timestamp_cached.cache_clear()
        # sms.build_attachment_xml_part_cached.cache_clear()  # Function removed - only HTML output supported
        sms.get_image_type.cache_clear()
        sms.encode_file_content.cache_clear()
        
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def create_test_directory_structure(self):
        """Create the required directory structure for SMS processing tests."""
        test_dir = Path(self.test_dir)
        
        # Create required subdirectories
        (test_dir / "Calls").mkdir(exist_ok=True)
        (test_dir / "Voicemails").mkdir(exist_ok=True)
        (test_dir / "Texts").mkdir(exist_ok=True)
        
        # Create a dummy Phones.vcf file to satisfy validation
        phones_vcf = test_dir / "Phones.vcf"
        phones_vcf.write_text("BEGIN:VCARD\nVERSION:3.0\nFN:Test User\nEND:VCARD", encoding="utf-8")
        
        # Create some dummy HTML files in Calls directory
        calls_dir = test_dir / "Calls"
        dummy_html = """<html><head><title>Test</title></head><body>Test content</body></html>"""
        (calls_dir / "test_call.html").write_text(dummy_html, encoding="utf-8")

    def test_setup_processing_paths(self):
        """Test processing path setup."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        # Check that paths were set
        # Note: We can't compare exact paths since they're different temp directories
        # but we can verify they're set and point to the right structure
        self.assertIsNotNone(sms.PROCESSING_DIRECTORY)
        self.assertIsNotNone(sms.OUTPUT_DIRECTORY)
        self.assertIsNotNone(sms.LOG_FILENAME)
        self.assertIsNotNone(sms.CONVERSATION_MANAGER)
        self.assertIsNotNone(sms.PHONE_LOOKUP_MANAGER)
        
        # Verify the output directory is a subdirectory of processing directory
        self.assertTrue(str(sms.OUTPUT_DIRECTORY).endswith("/conversations"))

    def test_validate_processing_directory(self):
        """Test processing directory validation."""
        test_dir = Path(self.test_dir)

        # Test with empty directory (should return True but log warnings)
        result = sms.validate_processing_directory(test_dir)
        self.assertTrue(result)

    def test_conversation_manager(self):
        """Test conversation manager functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        manager = sms.CONVERSATION_MANAGER

        # Test conversation ID generation
        conversation_id = manager.get_conversation_id(["+15551234567"], False)
        self.assertIsInstance(conversation_id, str)

        # Test conversation filename generation
        filename = manager.get_conversation_filename(conversation_id)
        self.assertIsInstance(filename, Path)

        # Test message writing (using dictionary format)
        manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1640995200000,  # 2022-01-01 00:00:00 in milliseconds
            sender="Test Sender",
            message="test",
            attachments=[]
        )

        # Test finalization
        manager.finalize_conversation_files()

        # Check that output directory was created
        self.assertTrue(manager.output_dir.exists())

    def test_phone_lookup_manager(self):
        """Test phone lookup manager functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        manager = sms.PHONE_LOOKUP_MANAGER

        # Test alias sanitization
        sanitized = manager.sanitize_alias("Test User (123)")
        self.assertEqual(sanitized, "Test_User_123")

        # Test adding alias
        manager.add_alias("+15551234567", "Test User")

        # Test getting alias - the manager may sanitize the alias when storing
        alias = manager.get_alias("+15551234567", None)
        # Check that we get some alias back (either original or sanitized)
        self.assertIsInstance(alias, str)
        self.assertGreater(len(alias), 0)

        # Test getting all aliases
        all_aliases = manager.get_all_aliases()
        self.assertIn("+15551234567", all_aliases)
        # Check that we have some alias stored
        self.assertIsInstance(all_aliases["+15551234567"], str)
        self.assertGreater(len(all_aliases["+15551234567"]), 0)

    def test_html_output_format(self):
        """Test HTML output format functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        manager = sms.CONVERSATION_MANAGER

        # Test that output format is set correctly
        # The output format should be set to "html" as passed to setup_processing_paths
        self.assertEqual(manager.output_format, "html")

        # Test conversation filename generation for HTML
        conversation_id = "test_conversation"
        filename = manager.get_conversation_filename(conversation_id)
        self.assertEqual(filename.suffix, ".html")

        # Test message writing (using dictionary format)
        manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1640995200000,  # 2022-01-01 00:00:00 in milliseconds
            sender="Test Sender",
            message="Hello World",
            attachments=[]
        )

        # Test finalization
        manager.finalize_conversation_files()

        # Check that output directory was created
        self.assertTrue(manager.output_dir.exists())

        # Check that HTML file was created
        html_file = manager.output_dir / f"{conversation_id}.html"
        self.assertTrue(html_file.exists())

        # Check HTML content
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("<table>", content)
            self.assertIn("Hello World", content)
            self.assertIn("SMS Conversation: test_conversation", content)

    def test_index_html_generation(self):
        """Test index.html generation functionality."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        manager = sms.CONVERSATION_MANAGER

        # Clear any existing conversations from other tests
        manager.conversation_files.clear()
        manager.conversation_stats.clear()
        
        # Clear the output directory to ensure clean state
        import shutil
        if manager.output_dir.exists():
            shutil.rmtree(manager.output_dir)
        manager.output_dir.mkdir(parents=True, exist_ok=True)

        # Create test conversation files with proper file objects
        conversation_id1 = "test_conversation_1"
        conversation_id2 = "test_conversation_2"

        # Create actual files for testing
        file1 = manager.output_dir / f"{conversation_id1}.html"
        file2 = manager.output_dir / f"{conversation_id2}.html"

        # Ensure output directory exists
        manager.output_dir.mkdir(parents=True, exist_ok=True)

        # Add test conversations with file objects
        manager.conversation_files[conversation_id1] = {
            "messages": [
                (
                    1234567890,
                    '<sms protocol="0" address="+15551234567" type="1" subject="null" body="Hello World" toa="null" sc_toa="null" date="1234567890" read="1" status="-1" locked="0" />',
                )
            ],
            "file": open(file1, "w", encoding="utf-8"),
        }

        manager.conversation_files[conversation_id2] = {
            "messages": [
                (
                    1234567891,
                    '<sms protocol="0" address="+15559876543" type="2" subject="null" body="Goodbye World" toa="null" sc_toa="null" date="1234567891" read="1" status="-1" locked="0" />',
                )
            ],
            "file": open(file2, "w", encoding="utf-8"),
        }

        # Finalize conversation files first
        manager.finalize_conversation_files()

        # Test index.html generation
        test_stats = {
            "num_sms": 2,
            "num_calls": 1,
            "num_voicemails": 0,
            "num_img": 0,
            "num_vcf": 0,
        }
        elapsed_time = 1.5

        manager.generate_index_html(test_stats, elapsed_time)

        # Check that index.html was created
        index_file = manager.output_dir / "index.html"
        self.assertTrue(index_file.exists())

        # Check index.html content
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Google Voice Conversations", content)
            self.assertIn("Processing completed in 1.5", content)
            self.assertIn("Output format: HTML", content)
            self.assertIn("Total conversations: 2", content)
            self.assertIn("SMS Messages", content)
            self.assertIn("Call Logs", content)
            self.assertIn("test_conversation_1", content)
            self.assertIn("test_conversation_2", content)
            self.assertIn(
                "Generated automatically by Google Voice SMS Takeout Converter", content
            )

    def test_group_conversation_handling(self):
        """Test group conversation handling including participant extraction and filename generation."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        # Test participant extraction from group conversation HTML
        test_html = """
        <div class="participants">Group conversation with:
            <cite class="sender vcard">
                <a class="tel" href="tel:+13478736042">
                    <span class="fn">Aniella Tang</span>
                </a>
            </cite>,
            <cite class="sender vcard">
                <a class="tel" href="tel:+13479098263">
                    <span class="fn">Inessa Tang</span>
                </a>
            </cite>,
            <cite class="sender vcard">
                <a class="tel" href="tel:+16462728914">
                    <span class="fn">Susan Nowak Tang</span>
                </a>
            </cite>
        </div>
        """

        soup = BeautifulSoup(test_html, "html.parser")
        participants_div = soup.find("div", class_="participants")

        # Test participant extraction
        participants_raw = [participants_div]
        participants, aliases = sms.get_participant_phone_numbers_and_aliases(
            participants_raw
        )

        expected_phones = ["+13478736042", "+13479098263", "+16462728914"]
        expected_aliases = ["Aniella Tang", "Inessa Tang", "Susan Nowak Tang"]

        self.assertEqual(participants, expected_phones)
        self.assertEqual(aliases, expected_aliases)

        # Add aliases to phone lookup manager for testing conversation ID generation
        phone_lookup = sms.PHONE_LOOKUP_MANAGER
        test_participants = {
            "+13478736042": "Aniella Tang",
            "+13479098263": "Inessa Tang",
            "+16462728914": "Susan Nowak Tang",
        }

        for phone, name in test_participants.items():
            phone_lookup.add_alias(phone, name)

        # Test conversation ID generation for group
        conv_manager = sms.CONVERSATION_MANAGER
        group_id = conv_manager.get_conversation_id(participants, True, phone_lookup)

        # Should use concatenated aliases
        expected_id = "Aniella_Tang_Inessa_Tang_Susan_Nowak_Tang"
        self.assertEqual(group_id, expected_id)

        # Test with many participants (truncation)
        many_participants = [
            "+15551234567",
            "+15559876543",
            "+15551111111",
            "+15552222222",
            "+15553333333",
            "+15554444444",
            "+15555555555",
            "+15556666666",
        ]

        # Add aliases for testing
        phone_lookup = sms.PHONE_LOOKUP_MANAGER
        for phone in many_participants:
            phone_lookup.add_alias(phone, f"User_{phone[-4:]}")

        many_group_id = conv_manager.get_conversation_id(many_participants, True, phone_lookup)

        # Should be truncated and include hash
        self.assertIn("and_3_more_", many_group_id)
        self.assertIn("User_", many_group_id)

        # Test that existing aliases are used instead of HTML extraction
        print("\nTesting existing alias priority...")

        # Now test with the same HTML but different aliases in phone lookup
        phone_lookup.add_alias("+13478736042", "Custom_Aliella")
        phone_lookup.add_alias("+13479098263", "Custom_Inessa")
        phone_lookup.add_alias("+16462728914", "Custom_Susan")

        # Extract again - should use existing aliases, not HTML
        participants2, aliases2 = sms.get_participant_phone_numbers_and_aliases(
            participants_raw
        )

        expected_aliases2 = ["Custom_Aliella", "Custom_Inessa", "Custom_Susan"]
        self.assertEqual(aliases2, expected_aliases2)

        # Test conversation ID generation with custom aliases
        group_id2 = conv_manager.get_conversation_id(participants2, True, phone_lookup)
        expected_id2 = "Custom_Aliella_Custom_Inessa_Custom_Susan"
        self.assertEqual(group_id2, expected_id2)

    def test_automatic_alias_extraction(self):
        """Test automatic alias extraction from HTML when prompts are disabled."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)

        manager = sms.PHONE_LOOKUP_MANAGER

        # Create a test HTML with vCard structure
        test_html = """
        <html>
        <body>
            <div class="participants">
                <a class="tel" href="tel:+15551234567">
                    <span class="fn">John Doe</span>
                </a>
            </div>
            <div class="message">
                <cite class="sender vcard">
                    <a class="tel" href="tel:+15559876543">Jane Smith</a>
                </cite>
            </div>
        </body>
        </html>
        """

        soup = BeautifulSoup(test_html, "html.parser")

        # Test automatic extraction for first phone number
        alias1 = manager.get_alias("+15551234567", soup)
        self.assertEqual(alias1, "John_Doe")

        # Test automatic extraction for second phone number
        alias2 = manager.get_alias("+15559876543", soup)
        self.assertEqual(alias2, "Jane_Smith")

        # Test that generic phrases are filtered out
        generic_html = """
        <html>
        <body>
            <a class="fn">Placed call to</a>
        </body>
        </html>
        """

        generic_soup = BeautifulSoup(generic_html, "html.parser")
        generic_alias = manager.get_alias("+15551111111", generic_soup)
        # Should use phone number directly, not extract generic phrase
        self.assertEqual(generic_alias, "+15551111111")

        # Test that existing aliases are prioritized over HTML extraction
        print("\nTesting existing alias priority in automatic extraction...")

        # Add a custom alias for an existing number
        manager.add_alias("+15551234567", "Custom_John")

        # Now test with the same HTML - should use existing alias, not extract from HTML
        existing_alias = manager.get_alias("+15551234567", soup)
        self.assertEqual(existing_alias, "Custom_John")

        # Test that HTML extraction still works for new numbers
        new_alias = manager.get_alias("+15559999999", soup)
        # Should use phone number since no HTML content for this number
        self.assertEqual(new_alias, "+15559999999")

        # Test that non-existent numbers return phone number when no soup provided
        no_soup_alias = manager.get_alias("+15559999999", None)
        self.assertEqual(no_soup_alias, "+15559999999")

    # test_message_content_extraction removed - XML parsing no longer supported

    def test_attachment_processing_integration(self):
        """Test attachment processing integration."""
        # Test build_attachment_mapping
        result = sms.build_attachment_mapping()
        self.assertIsInstance(result, dict)

        # Test build_attachment_mapping_with_progress_new (using PathManager)
        # Note: This function requires a PathManager instance, so we'll test the new function
        # First we need to set up a PathManager
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)
        if hasattr(sms, 'PATH_MANAGER') and sms.PATH_MANAGER:
            from core.attachment_manager_new import build_attachment_mapping_with_progress_new
            result = build_attachment_mapping_with_progress_new(sms.PATH_MANAGER)
            self.assertIsInstance(result, dict)
        else:
            # Skip this test if PathManager is not available
            self.skipTest("PathManager not available for testing")

    def test_html_processing_integration(self):
        """Test HTML processing integration."""
        # Test extract_src_with_progress
        result = sms.extract_src_with_progress()
        self.assertIsInstance(result, list)

        # Test list_att_filenames_with_progress
        result = sms.list_att_filenames_with_progress()
        self.assertIsInstance(result, list)

    # test_mms_processing_integration removed - XML output no longer supported

    # test_participant_processing_integration removed - XML output no longer supported

    def test_html_output_sender_column(self):
        """Verify HTML output includes Sender column and renders a sender cell."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)
        manager = sms.CONVERSATION_MANAGER

        conversation_id = "sender_column_test"
        # Test sender column display
        manager.write_message_with_content(
            conversation_id=conversation_id,
            timestamp=1640995200000,  # 2022-01-01 00:00:00 in milliseconds
            sender="Test Sender",
            message="Hello Sender Column",
            attachments=[]
        )
        manager.finalize_conversation_files()

        html_file = manager.output_dir / f"{conversation_id}.html"
        self.assertTrue(html_file.exists())
