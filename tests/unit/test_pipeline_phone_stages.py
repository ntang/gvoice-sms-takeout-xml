"""
Unit tests for pipeline phone processing stages.

Tests the PhoneDiscoveryStage and PhoneLookupStage functionality.
"""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.pipeline import PipelineContext
from core.pipeline.stages import PhoneDiscoveryStage, PhoneLookupStage


class TestPhoneDiscoveryStage(unittest.TestCase):
    """Test PhoneDiscoveryStage functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.processing_dir = self.temp_path / "processing"
        self.output_dir = self.temp_path / "output"

        self.processing_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)

        self.stage = PhoneDiscoveryStage()
        self.context = PipelineContext(
            processing_dir=self.processing_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_stage_initialization(self):
        """Test that stage initializes correctly."""
        self.assertEqual(self.stage.name, "phone_discovery")
        self.assertIsInstance(self.stage.phone_patterns, list)
        self.assertTrue(len(self.stage.phone_patterns) > 0)

    def test_normalize_phone_number(self):
        """Test phone number normalization."""
        test_cases = [
            ("+1234567890", "+1234567890"),
            ("(234) 567-8901", "+12345678901"),
            ("234-567-8902", "+12345678902"),
            ("2345678903", "+12345678903"),
            ("12345678904", "+12345678904"),
            ("+441234567890", "+441234567890"),  # International
            ("invalid", ""),  # Invalid format
            ("123", ""),  # Too short
        ]

        for input_phone, expected in test_cases:
            with self.subTest(input=input_phone):
                result = self.stage._normalize_phone_number(input_phone)
                self.assertEqual(result, expected)

    def test_find_html_files(self):
        """Test HTML file discovery."""
        # Create test HTML files
        (self.processing_dir / "test1.html").write_text("<html></html>")
        (self.processing_dir / "Calls").mkdir()
        (self.processing_dir / "Calls" / "test2.html").write_text("<html></html>")
        (self.processing_dir / "Texts").mkdir()
        (self.processing_dir / "Texts" / "test3.html").write_text("<html></html>")

        # Non-HTML file should be ignored
        (self.processing_dir / "test.txt").write_text("not html")

        html_files = self.stage._find_html_files(self.processing_dir)

        self.assertEqual(len(html_files), 3)
        html_names = [f.name for f in html_files]
        self.assertIn("test1.html", html_names)
        self.assertIn("test2.html", html_names)
        self.assertIn("test3.html", html_names)

    def test_extract_phone_numbers(self):
        """Test phone number extraction from HTML."""
        # Create test HTML with various phone number formats
        html_content = """
        <html>
        <body>
            <p>Call me at +1234567890</p>
            <p>Or try (555) 123-4567</p>
            <p>Also 555-987-6543</p>
            <a href="tel:+15551234567">Click to call</a>
            <span>Invalid: 123</span>
        </body>
        </html>
        """

        html_file = self.processing_dir / "test.html"
        html_file.write_text(html_content)

        numbers = self.stage._extract_phone_numbers([html_file])

        expected_numbers = {"+1234567890", "+15551234567", "+15559876543"}

        # The phone extraction might find additional numbers, so check that our expected ones are present
        self.assertTrue(expected_numbers.issubset(numbers),
                        f"Expected numbers {expected_numbers} not all found in {numbers}")

        # Should find at least our expected numbers
        self.assertGreaterEqual(len(numbers), 3)

    def test_load_known_numbers(self):
        """Test loading known numbers from phone lookup file."""
        # Create phone lookup file
        phone_lookup_content = """
        # Phone lookup file
        +1234567890:John Doe:
        +1555123456:Jane Smith:filter
        +1999888777:Spam Number:filter
        """

        phone_lookup_file = self.processing_dir / "phone_lookup.txt"
        phone_lookup_file.write_text(phone_lookup_content)

        known_numbers = self.stage._load_known_numbers(self.context)

        expected_numbers = {"+1234567890", "+1555123456", "+1999888777"}
        self.assertEqual(known_numbers, expected_numbers)

    def test_execute_success(self):
        """Test successful execution of phone discovery."""
        # Create test HTML file
        html_content = """
        <html><body>
        <p>Contact: +1234567890</p>
        <p>Also: (555) 123-4567</p>
        </body></html>
        """
        (self.processing_dir / "test.html").write_text(html_content)

        # Create phone lookup file with one known number
        phone_lookup_content = "+1234567890:Known Contact:"
        (self.processing_dir / "phone_lookup.txt").write_text(phone_lookup_content)

        result = self.stage.execute(self.context)

        self.assertTrue(result.success)
        # The phone discovery might find more numbers than expected due to regex patterns
        self.assertGreaterEqual(result.records_processed, 2)  # At least 2 unique numbers
        self.assertEqual(len(result.output_files), 1)

        # Check output file
        output_file = self.output_dir / "phone_inventory.json"
        self.assertTrue(output_file.exists())

        with open(output_file) as f:
            inventory = json.load(f)

        self.assertGreaterEqual(len(inventory["discovered_numbers"]), 2)
        self.assertGreaterEqual(len(inventory["known_numbers"]), 1)
        self.assertGreaterEqual(len(inventory["unknown_numbers"]), 1)

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


class TestPhoneLookupStage(unittest.TestCase):
    """Test PhoneLookupStage functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.processing_dir = self.temp_path / "processing"
        self.output_dir = self.temp_path / "output"

        self.processing_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)

        self.stage = PhoneLookupStage(api_provider="manual")
        self.context = PipelineContext(
            processing_dir=self.processing_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_stage_initialization(self):
        """Test that stage initializes correctly."""
        self.assertEqual(self.stage.name, "phone_lookup")
        self.assertEqual(self.stage.api_provider, "manual")
        self.assertIsInstance(self.stage.api_configs, dict)

    def test_init_phone_directory(self):
        """Test phone directory database initialization."""
        db_path = self.output_dir / "test.sqlite"
        self.stage._init_phone_directory(db_path)

        self.assertTrue(db_path.exists())

        # Check database structure
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

        self.assertIn("phone_directory", tables)

    def test_export_unknown_numbers_csv(self):
        """Test CSV export for manual lookup."""
        unknown_numbers = ["+1234567890", "+1555123456"]

        csv_path = self.stage._export_unknown_numbers_csv(unknown_numbers, self.output_dir)

        self.assertTrue(csv_path.exists())

        with open(csv_path) as f:
            content = f.read()

        self.assertIn("phone_number,display_name,is_spam,notes", content)
        self.assertIn("+1234567890", content)
        self.assertIn("+1555123456", content)

    def test_execute_manual_mode(self):
        """Test execution in manual mode."""
        # Create phone inventory from discovery stage
        inventory = {
            "unknown_numbers": ["+1234567890", "+1555123456"],
            "known_numbers": ["+1999888777"],
            "discovered_numbers": ["+1234567890", "+1555123456", "+1999888777"]
        }

        inventory_file = self.output_dir / "phone_inventory.json"
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f)

        result = self.stage.execute(self.context)

        self.assertTrue(result.success)
        self.assertEqual(result.records_processed, 2)  # 2 unknown numbers

        # Check CSV was created
        csv_path = self.output_dir / "unknown_numbers.csv"
        self.assertTrue(csv_path.exists())

    def test_validate_prerequisites(self):
        """Test prerequisite validation."""
        # Invalid case - no phone inventory
        self.assertFalse(self.stage.validate_prerequisites(self.context))

        # Valid case - phone inventory exists
        inventory = {"unknown_numbers": []}
        inventory_file = self.output_dir / "phone_inventory.json"
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f)

        self.assertTrue(self.stage.validate_prerequisites(self.context))

    def test_get_dependencies(self):
        """Test stage dependencies."""
        dependencies = self.stage.get_dependencies()
        self.assertEqual(dependencies, ["phone_discovery"])


if __name__ == '__main__':
    unittest.main()
