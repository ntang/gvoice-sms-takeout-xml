"""
File Type Processor Module for SMS/MMS conversion.

This module handles the processing of different types of HTML files (SMS, MMS, calls, voicemails)
and coordinates the extraction and processing of their content.
"""

import logging
from pathlib import Path
from typing import Dict, Union, Optional
from bs4 import BeautifulSoup

from .html_processor import (
    parse_html_file,
    get_file_type,
    should_skip_file,
)
from core.conversation_manager import ConversationManager
from core.phone_lookup import PhoneLookupManager

logger = logging.getLogger(__name__)


def process_single_html_file(
    html_file: Path,
    src_filename_map: Dict[str, str],
    own_number: Optional[str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager,
) -> Dict[str, Union[int, str]]:
    """
    Process a single HTML file and return statistics.

    Args:
        html_file: Path to the HTML file to process
        src_filename_map: Mapping of src elements to attachment filenames
        own_number: User's own phone number
        conversation_manager: Manager for conversation handling
        phone_lookup_manager: Manager for phone number lookups

    Returns:
        Dictionary containing processing statistics
    """
    try:
        # Parse the HTML file
        soup = parse_html_file(html_file)

        # Determine file type
        file_type = get_file_type(html_file.name)

        # Process based on file type
        if file_type == "sms_mms":
            return process_sms_mms_file(
                html_file,
                soup,
                own_number,
                src_filename_map,
                conversation_manager,
                phone_lookup_manager,
            )
        elif file_type == "call":
            return process_call_file(
                html_file,
                soup,
                own_number,
                src_filename_map,
                conversation_manager,
                phone_lookup_manager,
            )
        elif file_type == "voicemail":
            return process_voicemail_file(
                html_file,
                soup,
                own_number,
                src_filename_map,
                conversation_manager,
                phone_lookup_manager,
            )
        else:
            logger.warning(f"Unknown file type '{file_type}' for {html_file.name}")
            return {
                "num_sms": 0,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": own_number,
            }

    except Exception as e:
        logger.error(f"Failed to process {html_file.name}: {e}")
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "own_number": own_number,
        }


def process_sms_mms_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager,
) -> Dict[str, Union[int, str]]:
    """
    Process SMS/MMS files by calling the appropriate function from sms.py.
    """
    # Import the actual function from sms.py
    from sms import process_sms_mms_file as sms_process_sms_mms_file

    # Call the function with the correct parameters
    return sms_process_sms_mms_file(
        html_file,
        soup,
        own_number,
        src_filename_map,
        conversation_manager,
        phone_lookup_manager,
    )


def process_call_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager,
) -> Dict[str, Union[int, str]]:
    """
    Process call files by calling the appropriate function from sms.py.
    """
    # Import the actual function from sms.py
    from sms import extract_call_info

    # Call the function with the correct parameters (only filename and soup)
    call_info = extract_call_info(str(html_file), soup)

    # Return statistics based on whether call info was extracted
    if call_info:
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 1,
            "num_voicemails": 0,
            "own_number": own_number,
        }
    else:
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "own_number": own_number,
        }


def process_voicemail_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager,
) -> Dict[str, Union[int, str]]:
    """
    Process voicemail files by calling the appropriate function from sms.py.
    """
    # Import the actual function from sms.py
    from sms import extract_voicemail_info

    # Call the function with the correct parameters (only filename and soup)
    voicemail_info = extract_voicemail_info(str(html_file), soup)

    # Return statistics based on whether voicemail info was extracted
    if voicemail_info:
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 1,
            "own_number": own_number,
        }
    else:
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "own_number": own_number,
        }


def get_file_processing_stats(html_files: list) -> Dict[str, int]:
    """
    Get statistics about the types of files to be processed.

    Args:
        html_files: List of HTML files to analyze

    Returns:
        Dictionary containing file type counts
    """
    stats = {"sms_mms": 0, "call": 0, "voicemail": 0, "unknown": 0}

    for html_file in html_files:
        file_type = get_file_type(html_file.name)
        if file_type in stats:
            stats[file_type] += 1
        else:
            stats["unknown"] += 1

    return stats


def validate_file_for_processing(html_file: Path) -> Dict[str, Union[bool, str]]:
    """
    Validate that a file is suitable for processing.

    Args:
        html_file: Path to the HTML file to validate

    Returns:
        Dictionary containing validation results
    """
    try:
        # Check if file exists and is readable
        if not html_file.exists():
            return {"valid": False, "error": "File does not exist"}

        if not html_file.is_file():
            return {"valid": False, "error": "Path is not a file"}

        # Check file extension
        if html_file.suffix.lower() != ".html":
            return {"valid": False, "error": "File is not an HTML file"}

        # Check if file should be skipped
        if should_skip_file(html_file.name):
            return {"valid": False, "error": "File should be skipped"}

        return {"valid": True, "error": None}

    except Exception as e:
        return {"valid": False, "error": f"Validation error: {e}"}
