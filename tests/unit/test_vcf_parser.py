"""
Unit tests for VCF (vCard) parser.

Tests the extraction of the user's own phone number from Phones.vcf file.
Following TDD: These tests are written FIRST and will fail until implementation is complete.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

# Import the function we'll be testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.vcf_parser import extract_own_number_from_vcf


class TestVCFParser:
    """Test VCF parsing for own number extraction."""

    def test_extract_own_number_from_valid_vcf(self):
        """Test extraction from real Phones.vcf format."""
        # Create a temporary VCF file with Google Voice export format
        vcf_content = """BEGIN:VCARD
VERSION:3.0
FN:
N:;;;;
item1.TEL:+13474106066
item1.X-ABLabel:Google Voice
TEL;TYPE=CELL:+13473865957
TEL;TYPE=CELL:+16313611005
END:VCARD"""
        
        with TemporaryDirectory() as tmpdir:
            vcf_file = Path(tmpdir) / "Phones.vcf"
            vcf_file.write_text(vcf_content)
            
            # Extract own number
            own_number = extract_own_number_from_vcf(vcf_file)
            
            # Should return the Google Voice number in E164 format
            assert own_number == "+13474106066"

    def test_extract_own_number_google_voice_label(self):
        """Test that it specifically finds the number with X-ABLabel:Google Voice."""
        # VCF with multiple numbers - should pick the Google Voice one
        vcf_content = """BEGIN:VCARD
VERSION:3.0
FN:User Name
TEL;TYPE=CELL:+19995551234
item1.TEL:+13474106066
item1.X-ABLabel:Google Voice
TEL;TYPE=CELL:+16313611005
END:VCARD"""
        
        with TemporaryDirectory() as tmpdir:
            vcf_file = Path(tmpdir) / "Phones.vcf"
            vcf_file.write_text(vcf_content)
            
            own_number = extract_own_number_from_vcf(vcf_file)
            
            # Should return the Google Voice number, not the other numbers
            assert own_number == "+13474106066"
            assert own_number != "+19995551234"
            assert own_number != "+16313611005"

    def test_extract_own_number_normalizes_to_e164(self):
        """Test that phone numbers are normalized to E164 format."""
        # VCF with unformatted number
        vcf_content = """BEGIN:VCARD
VERSION:3.0
item1.TEL:347-410-6066
item1.X-ABLabel:Google Voice
END:VCARD"""
        
        with TemporaryDirectory() as tmpdir:
            vcf_file = Path(tmpdir) / "Phones.vcf"
            vcf_file.write_text(vcf_content)
            
            own_number = extract_own_number_from_vcf(vcf_file)
            
            # Should normalize to E164 format
            assert own_number == "+13474106066"

    def test_extract_own_number_missing_file(self):
        """Test behavior when Phones.vcf file doesn't exist."""
        non_existent_file = Path("/tmp/does_not_exist_123456789.vcf")
        
        own_number = extract_own_number_from_vcf(non_existent_file)
        
        # Should return None for missing file
        assert own_number is None

    def test_extract_own_number_malformed_vcf(self):
        """Test behavior with malformed VCF file."""
        vcf_content = """This is not a valid VCF file
Just some random text
No phone numbers here"""
        
        with TemporaryDirectory() as tmpdir:
            vcf_file = Path(tmpdir) / "Phones.vcf"
            vcf_file.write_text(vcf_content)
            
            own_number = extract_own_number_from_vcf(vcf_file)
            
            # Should return None for malformed VCF
            assert own_number is None

    def test_extract_own_number_no_google_voice_label(self):
        """Test VCF without Google Voice label."""
        vcf_content = """BEGIN:VCARD
VERSION:3.0
TEL;TYPE=CELL:+13474106066
TEL;TYPE=CELL:+13473865957
END:VCARD"""
        
        with TemporaryDirectory() as tmpdir:
            vcf_file = Path(tmpdir) / "Phones.vcf"
            vcf_file.write_text(vcf_content)
            
            own_number = extract_own_number_from_vcf(vcf_file)
            
            # Should return the first valid number as fallback
            assert own_number == "+13474106066"

    def test_extract_own_number_empty_file(self):
        """Test behavior with empty VCF file."""
        with TemporaryDirectory() as tmpdir:
            vcf_file = Path(tmpdir) / "Phones.vcf"
            vcf_file.write_text("")
            
            own_number = extract_own_number_from_vcf(vcf_file)
            
            # Should return None for empty file
            assert own_number is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

