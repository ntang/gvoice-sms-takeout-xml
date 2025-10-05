"""
Unit tests for pipeline file processing stages.

Tests the FileDiscoveryStage and ContentExtractionStage functionality.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.pipeline import PipelineContext
from core.pipeline.stages import FileDiscoveryStage, ContentExtractionStage


class TestFileDiscoveryStage(unittest.TestCase):
    """Test FileDiscoveryStage functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.processing_dir = self.temp_path / "processing"
        self.output_dir = self.temp_path / "output"

        self.processing_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)

        self.stage = FileDiscoveryStage()
        self.context = PipelineContext(
            processing_dir=self.processing_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_stage_initialization(self):
        """Test that stage initializes correctly."""
        self.assertEqual(self.stage.name, "file_discovery")
        self.assertIsInstance(self.stage.file_type_patterns, dict)
        self.assertIn("sms_mms", self.stage.file_type_patterns)
        self.assertIn("calls", self.stage.file_type_patterns)
        self.assertIn("voicemails", self.stage.file_type_patterns)

    def test_discover_html_files(self):
        """Test HTML file discovery."""
        # Create test HTML files in different directories
        (self.processing_dir / "test1.html").write_text("<html></html>")

        calls_dir = self.processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "call1.html").write_text("<html></html>")

        texts_dir = self.processing_dir / "Texts"
        texts_dir.mkdir()
        (texts_dir / "text1.html").write_text("<html></html>")

        voicemails_dir = self.processing_dir / "Voicemails"
        voicemails_dir.mkdir()
        (voicemails_dir / "vm1.html").write_text("<html></html>")

        # Non-HTML file should be ignored
        (self.processing_dir / "test.txt").write_text("not html")

        html_files = self.stage._discover_html_files(self.processing_dir)

        self.assertEqual(len(html_files), 4)
        html_names = [f.name for f in html_files]
        self.assertIn("test1.html", html_names)
        self.assertIn("call1.html", html_names)
        self.assertIn("text1.html", html_names)
        self.assertIn("vm1.html", html_names)

    def test_analyze_file(self):
        """Test file analysis and metadata extraction."""
        # Create test HTML file with SMS content
        html_content = """
        <html>
        <head><title>Conversation with John Doe</title></head>
        <body>
            <div class="message">Hello there!</div>
            <div class="message">How are you?</div>
        </body>
        </html>
        """

        texts_dir = self.processing_dir / "Texts"
        texts_dir.mkdir()
        html_file = texts_dir / "john_doe.html"
        html_file.write_text(html_content)

        file_info = self.stage._analyze_file(html_file, self.processing_dir)

        self.assertEqual(file_info["type"], "sms_mms")
        self.assertEqual(file_info["directory"], "Texts")
        self.assertEqual(file_info["filename"], "john_doe.html")
        self.assertGreater(file_info["size_bytes"], 0)
        self.assertIsNotNone(file_info["modified_time"])

    def test_detect_file_type_by_content(self):
        """Test file type detection by content analysis."""
        # SMS/MMS content
        sms_content = """
        <html><body>
        <div class="message-text">Hello world</div>
        </body></html>
        """
        sms_file = self.processing_dir / "sms_test.html"
        sms_file.write_text(sms_content)

        file_type = self.stage._detect_file_type_by_content(sms_file)
        self.assertEqual(file_type, "sms_mms")

        # Call content
        call_content = """
        <html><body>
        <div class="call-log">Call duration: 5 minutes</div>
        </body></html>
        """
        call_file = self.processing_dir / "call_test.html"
        call_file.write_text(call_content)

        file_type = self.stage._detect_file_type_by_content(call_file)
        self.assertEqual(file_type, "calls")

    def test_execute_success(self):
        """Test successful execution of file discovery."""
        # Create test HTML files
        (self.processing_dir / "test1.html").write_text("<html><body>Test</body></html>")

        calls_dir = self.processing_dir / "Calls"
        calls_dir.mkdir()
        (calls_dir / "call1.html").write_text("<html><body>Call log</body></html>")

        result = self.stage.execute(self.context)

        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 2)
        self.assertEqual(len(result.output_files), 1)

        # Check output file
        output_file = self.output_dir / "file_inventory.json"
        self.assertTrue(output_file.exists())

        with open(output_file) as f:
            inventory = json.load(f)

        self.assertEqual(len(inventory["files"]), 2)
        self.assertIn("discovery_metadata", inventory)
        self.assertIn("summary", inventory)

    def test_validate_prerequisites(self):
        """Test prerequisite validation."""
        # Valid case
        self.assertTrue(self.stage.validate_prerequisites(self.context))

        # Invalid case - processing directory doesn't exist
        invalid_context = PipelineContext(
            processing_dir=Path("/nonexistent"),
            output_dir=self.output_dir
        )
        self.assertFalse(self.stage.validate_prerequisites(invalid_context))


class TestContentExtractionStage(unittest.TestCase):
    """Test ContentExtractionStage functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.processing_dir = self.temp_path / "processing"
        self.output_dir = self.temp_path / "output"

        self.processing_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)

        self.stage = ContentExtractionStage(max_files_per_batch=5)
        self.context = PipelineContext(
            processing_dir=self.processing_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_stage_initialization(self):
        """Test that stage initializes correctly."""
        self.assertEqual(self.stage.name, "content_extraction")
        self.assertEqual(self.stage.max_files_per_batch, 5)
        self.assertIsInstance(self.stage.timestamp_patterns, list)
        self.assertTrue(len(self.stage.timestamp_patterns) > 0)

    def test_extract_sms_mms_content(self):
        """Test SMS/MMS content extraction."""
        # Create test SMS HTML file
        html_content = """
        <html>
        <head><title>Conversation with Jane Smith</title></head>
        <body>
            <div class="message">
                <span class="timestamp">Jan 15, 2023 2:30:45 PM</span>
                <span class="sender">+1234567890</span>
                <span class="text">Hello there!</span>
            </div>
            <div class="message">
                <span class="timestamp">Jan 15, 2023 2:31:00 PM</span>
                <span class="text">How are you doing?</span>
            </div>
        </body>
        </html>
        """

        html_file = self.processing_dir / "jane_smith.html"
        html_file.write_text(html_content)

        file_info = {
            "path": str(html_file),
            "type": "sms_mms",
            "size_bytes": len(html_content)
        }

        conversation = self.stage._extract_sms_mms_content(html_file, file_info)

        self.assertIsNotNone(conversation)
        self.assertEqual(conversation["conversation_id"], "jane_smith")
        self.assertEqual(conversation["file_type"], "sms_mms")
        # Check that we have participants (could be "Conversation with Jane Smith" or extracted names)
        self.assertGreater(len(conversation["participants"]), 0)
        # Check that the title-based participant is present
        title_participants = [p for p in conversation["participants"] if "Jane Smith" in p]
        self.assertGreater(len(title_participants), 0)
        self.assertIsInstance(conversation["messages"], list)

    def test_extract_messages_from_soup(self):
        """Test message extraction from BeautifulSoup object."""
        from bs4 import BeautifulSoup

        html_content = """
        <html><body>
            <div class="message">
                Jan 15, 2023 2:30:45 PM +1234567890: Hello world!
            </div>
            <div class="message">
                Jan 15, 2023 2:31:00 PM: Reply message
            </div>
        </body></html>
        """

        soup = BeautifulSoup(html_content, 'html.parser')
        messages = self.stage._extract_messages_from_soup(soup, "sms_mms")

        self.assertGreater(len(messages), 0)

        # Check first message
        if messages:
            message = messages[0]
            self.assertIn("content", message)
            self.assertIn("message_type", message)
            self.assertEqual(message["message_type"], "sms_mms")

    def test_execute_with_file_inventory(self):
        """Test execution with file inventory from discovery stage."""
        # Create file inventory
        inventory = {
            "files": [
                {
                    "path": str(self.processing_dir / "test1.html"),
                    "type": "sms_mms",
                    "size_bytes": 1000
                },
                {
                    "path": str(self.processing_dir / "test2.html"),
                    "type": "calls",
                    "size_bytes": 500
                }
            ]
        }

        inventory_file = self.output_dir / "file_inventory.json"
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f)

        # Create corresponding HTML files
        (self.processing_dir / "test1.html").write_text("""
        <html><body>
        <div class="message">Test message</div>
        </body></html>
        """)

        (self.processing_dir / "test2.html").write_text("""
        <html><body>
        <div class="call">Test call</div>
        </body></html>
        """)

        result = self.stage.execute(self.context)

        self.assertTrue(result.success)
        self.assertGreaterEqual(result.records_processed, 2)

        # Check output file
        output_file = self.output_dir / "extracted_content.json"
        self.assertTrue(output_file.exists())

        with open(output_file) as f:
            content = json.load(f)

        self.assertIn("conversations", content)
        self.assertIn("extraction_metadata", content)

    def test_validate_prerequisites(self):
        """Test prerequisite validation."""
        # Invalid case - no file inventory
        self.assertFalse(self.stage.validate_prerequisites(self.context))

        # Valid case - file inventory exists
        inventory = {"files": []}
        inventory_file = self.output_dir / "file_inventory.json"
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f)

        self.assertTrue(self.stage.validate_prerequisites(self.context))

    def test_get_dependencies(self):
        """Test stage dependencies."""
        dependencies = self.stage.get_dependencies()
        self.assertEqual(dependencies, ["file_discovery"])


if __name__ == '__main__':
    unittest.main()
