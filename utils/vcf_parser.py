"""
VCF (vCard) Parser for Google Voice Takeout.

This module extracts the user's own phone number from the Phones.vcf file
that is included in Google Voice Takeout exports.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import phonenumbers
from phonenumbers import format_number, PhoneNumberFormat

logger = logging.getLogger(__name__)


def extract_own_number_from_vcf(vcf_file_path: Path) -> Optional[str]:
    """
    Extract user's own phone number from Phones.vcf file.
    
    Looks for the phone number marked with "X-ABLabel:Google Voice" which
    indicates the user's Google Voice number. If not found, returns the
    first valid phone number as a fallback.
    
    Args:
        vcf_file_path: Path to Phones.vcf file
        
    Returns:
        User's Google Voice number in E164 format (+1XXXXXXXXXX), or None if not found
    """
    try:
        # Check if file exists
        if not vcf_file_path or not vcf_file_path.exists():
            logger.debug(f"VCF file not found: {vcf_file_path}")
            return None
        
        # Read VCF file
        try:
            vcf_content = vcf_file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.debug(f"Failed to read VCF file {vcf_file_path}: {e}")
            return None
        
        if not vcf_content or not vcf_content.strip():
            logger.debug("VCF file is empty")
            return None
        
        # Parse VCF line by line
        lines = vcf_content.split('\n')
        
        # Strategy 1: Find number with X-ABLabel:Google Voice
        google_voice_number = _extract_google_voice_number(lines)
        if google_voice_number:
            logger.debug(f"Found Google Voice number in VCF: {google_voice_number}")
            return google_voice_number
        
        # Strategy 2: Fallback - extract first valid phone number
        first_number = _extract_first_phone_number(lines)
        if first_number:
            logger.debug(f"Using first phone number from VCF as fallback: {first_number}")
            return first_number
        
        logger.debug("No valid phone numbers found in VCF file")
        return None
        
    except Exception as e:
        logger.error(f"Failed to extract own number from VCF: {e}")
        return None


def _extract_google_voice_number(lines: list) -> Optional[str]:
    """
    Extract the phone number marked with X-ABLabel:Google Voice.
    
    Args:
        lines: List of lines from VCF file
        
    Returns:
        Google Voice number in E164 format, or None
    """
    try:
        # Find the line with "X-ABLabel:Google Voice"
        for i, line in enumerate(lines):
            if "X-ABLabel:Google Voice" in line or "X-ABLabel:GOOGLE VOICE" in line.upper():
                # Look backwards for the corresponding TEL line
                # Usually it's on the line immediately before the X-ABLabel
                for j in range(i - 1, max(0, i - 5), -1):
                    tel_line = lines[j]
                    if "TEL:" in tel_line.upper():
                        # Extract phone number from TEL line
                        phone_number = _parse_tel_line(tel_line)
                        if phone_number:
                            return phone_number
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to extract Google Voice number: {e}")
        return None


def _extract_first_phone_number(lines: list) -> Optional[str]:
    """
    Extract the first valid phone number from VCF.
    
    Args:
        lines: List of lines from VCF file
        
    Returns:
        First phone number in E164 format, or None
    """
    try:
        for line in lines:
            # Check for any TEL field (with or without type specifier)
            if "TEL" in line.upper() and ":" in line:
                phone_number = _parse_tel_line(line)
                if phone_number:
                    return phone_number
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to extract first phone number: {e}")
        return None


def _parse_tel_line(tel_line: str) -> Optional[str]:
    """
    Parse a TEL: line from VCF and extract the phone number.
    
    Args:
        tel_line: Line containing TEL: field
        
    Returns:
        Normalized phone number in E164 format, or None
    """
    try:
        # Extract the value after TEL: or TEL;TYPE=...:
        # Formats: "TEL:+1234567890" or "item1.TEL:+1234567890" or "TEL;TYPE=CELL:+1234567890"
        
        # Split on colon to get the phone number part
        if ':' in tel_line:
            phone_part = tel_line.split(':', 1)[1].strip()
        else:
            return None
        
        # Clean up any remaining formatting
        phone_part = phone_part.strip()
        
        # Try to parse and normalize the phone number
        try:
            # Parse assuming US region (Google Voice is US-based)
            parsed_number = phonenumbers.parse(phone_part, "US")
            
            # Validate the number
            if phonenumbers.is_valid_number(parsed_number):
                # Format to E164 standard
                normalized = format_number(parsed_number, PhoneNumberFormat.E164)
                return normalized
            else:
                logger.debug(f"Invalid phone number in VCF: {phone_part}")
                return None
                
        except phonenumbers.phonenumberutil.NumberParseException as e:
            logger.debug(f"Failed to parse phone number from VCF line '{tel_line}': {e}")
            return None
        
    except Exception as e:
        logger.debug(f"Failed to parse TEL line: {e}")
        return None


def extract_all_numbers_from_vcf(vcf_file_path: Path) -> list:
    """
    Extract all phone numbers from Phones.vcf file.
    
    Useful for debugging and analyzing VCF contents.
    
    Args:
        vcf_file_path: Path to Phones.vcf file
        
    Returns:
        List of phone numbers in E164 format
    """
    try:
        if not vcf_file_path or not vcf_file_path.exists():
            return []
        
        vcf_content = vcf_file_path.read_text(encoding='utf-8')
        lines = vcf_content.split('\n')
        
        numbers = []
        for line in lines:
            if "TEL:" in line.upper():
                phone_number = _parse_tel_line(line)
                if phone_number:
                    numbers.append(phone_number)
        
        return numbers
        
    except Exception as e:
        logger.error(f"Failed to extract all numbers from VCF: {e}")
        return []

