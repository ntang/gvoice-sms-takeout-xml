"""
File Type Processor Module for SMS/MMS conversion.

This module handles the processing of different types of HTML files (SMS, MMS, calls, voicemails)
and coordinates the extraction and processing of their content.
"""

import logging
from pathlib import Path
from typing import Dict, Union, Optional
from bs4 import BeautifulSoup

from html_processor import parse_html_file, get_file_type, should_skip_file, extract_own_phone_number
from conversation_manager import ConversationManager
from phone_lookup import PhoneLookupManager

logger = logging.getLogger(__name__)


def process_single_html_file(
    html_file: Path, 
    src_filename_map: Dict[str, str], 
    own_number: Optional[str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager
) -> Dict[str, Union[int, str]]:
    """
    Process a single HTML file and return file-specific statistics.
    
    Args:
        html_file: Path to the HTML file to process
        src_filename_map: Mapping of src elements to attachment filenames
        own_number: User's own phone number
        conversation_manager: Manager for conversation files
        phone_lookup_manager: Manager for phone number lookups
        
    Returns:
        Dictionary with processing statistics and extracted information
    """
    
    # Check if file should be skipped before processing
    if should_skip_file(html_file.name):
        logger.debug(f"Skipping corrupted or invalid file: {html_file.name}")
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "own_number": own_number,
        }
    
    file_type = get_file_type(html_file.name)
    logger.debug(f"Processing {html_file.name} (Type: {file_type})")

    # Parse HTML file
    soup = parse_html_file(html_file)

    # Extract own phone number if not already found
    if own_number is None:
        own_number = extract_own_phone_number(soup)

    # Handle different file types
    if file_type == "call":
        return process_call_file(html_file, soup, own_number, src_filename_map, conversation_manager, phone_lookup_manager)
    elif file_type == "voicemail":
        return process_voicemail_file(html_file, soup, own_number, src_filename_map, conversation_manager, phone_lookup_manager)
    else:
        # Process SMS/MMS files
        return process_sms_mms_file(html_file, soup, own_number, src_filename_map, conversation_manager, phone_lookup_manager)


def process_sms_mms_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager
) -> Dict[str, Union[int, str]]:
    """
    Process SMS/MMS files and return statistics.
    
    Args:
        html_file: Path to the HTML file
        soup: BeautifulSoup object of the HTML content
        own_number: User's own phone number
        src_filename_map: Mapping of src elements to attachment filenames
        conversation_manager: Manager for conversation files
        phone_lookup_manager: Manager for phone number lookups
        
    Returns:
        Dictionary with processing statistics
    """
    from sms_processor import process_sms_messages, process_mms_messages
    
    stats = {
        "num_sms": 0,
        "num_img": 0,
        "num_vcf": 0,
        "num_calls": 0,
        "num_voicemails": 0,
        "own_number": own_number,
    }
    
    try:
        # Process SMS messages
        sms_stats = process_sms_messages(html_file, soup, own_number, src_filename_map, conversation_manager, phone_lookup_manager)
        stats["num_sms"] += sms_stats.get("num_sms", 0)
        stats["num_img"] += sms_stats.get("num_img", 0)
        stats["num_vcf"] += sms_stats.get("num_vcf", 0)
        
        # Process MMS messages if any
        mms_stats = process_mms_messages(html_file, soup, own_number, src_filename_map, conversation_manager, phone_lookup_manager)
        stats["num_sms"] += mms_stats.get("num_sms", 0)
        stats["num_img"] += mms_stats.get("num_img", 0)
        stats["num_vcf"] += mms_stats.get("num_vcf", 0)
        
    except Exception as e:
        logger.error(f"Failed to process SMS/MMS file {html_file}: {e}")
        
    return stats


def process_call_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager
) -> Dict[str, Union[int, str]]:
    """
    Process call files and return statistics.
    
    Args:
        html_file: Path to the HTML file
        soup: BeautifulSoup object of the HTML content
        own_number: User's own phone number
        src_filename_map: Mapping of src elements to attachment filenames
        conversation_manager: Manager for conversation files
        phone_lookup_manager: Manager for phone number lookups
        
    Returns:
        Dictionary with processing statistics
    """
    from sms_processor import extract_call_info
    
    stats = {
        "num_sms": 0,
        "num_img": 0,
        "num_vcf": 0,
        "num_calls": 1,  # This is a call file
        "num_voicemails": 0,
        "own_number": own_number,
    }
    
    try:
        # Extract call information
        call_info = extract_call_info(html_file, soup, own_number, phone_lookup_manager)
        if call_info:
            # Add call to conversation manager
            conversation_manager.add_call_to_conversation(call_info)
            
    except Exception as e:
        logger.error(f"Failed to process call file {html_file}: {e}")
        
    return stats


def process_voicemail_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager
) -> Dict[str, Union[int, str]]:
    """
    Process voicemail files and return statistics.
    
    Args:
        html_file: Path to the HTML file
        soup: BeautifulSoup object of the HTML content
        own_number: User's own phone number
        src_filename_map: Mapping of src elements to attachment filenames
        conversation_manager: Manager for conversation files
        phone_lookup_manager: Manager for phone number lookups
        
    Returns:
        Dictionary with processing statistics
    """
    from sms_processor import extract_voicemail_info
    
    stats = {
        "num_sms": 0,
        "num_img": 0,
        "num_vcf": 0,
        "num_calls": 0,
        "num_voicemails": 1,  # This is a voicemail file
        "own_number": own_number,
    }
    
    try:
        # Extract voicemail information
        voicemail_info = extract_voicemail_info(html_file, soup, own_number, phone_lookup_manager)
        if voicemail_info:
            # Add voicemail to conversation manager
            conversation_manager.add_voicemail_to_conversation(voicemail_info)
            
    except Exception as e:
        logger.error(f"Failed to process voicemail file {html_file}: {e}")
        
    return stats


def get_file_processing_stats(html_files: list) -> Dict[str, int]:
    """
    Get statistics about the files to be processed.
    
    Args:
        html_files: List of HTML file paths
        
    Returns:
        Dictionary with file type counts
    """
    stats = {
        "total_files": len(html_files),
        "sms_files": 0,
        "mms_files": 0,
        "call_files": 0,
        "voicemail_files": 0,
        "unknown_files": 0,
    }
    
    for html_file in html_files:
        file_type = get_file_type(html_file.name)
        if file_type == "sms":
            stats["sms_files"] += 1
        elif file_type == "mms":
            stats["mms_files"] += 1
        elif file_type == "call":
            stats["call_files"] += 1
        elif file_type == "voicemail":
            stats["voicemail_files"] += 1
        else:
            stats["unknown_files"] += 1
            
    return stats


def validate_file_for_processing(html_file: Path) -> Dict[str, Union[bool, str]]:
    """
    Validate that a file is suitable for processing.
    
    Args:
        html_file: Path to the HTML file to validate
        
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "valid": True,
        "reason": "",
        "file_type": "",
        "size": 0,
    }
    
    try:
        # Check if file exists and is readable
        if not html_file.exists():
            validation_result["valid"] = False
            validation_result["reason"] = "File does not exist"
            return validation_result
            
        if not html_file.is_file():
            validation_result["valid"] = False
            validation_result["reason"] = "Path is not a file"
            return validation_result
            
        # Check file size
        file_size = html_file.stat().st_size
        validation_result["size"] = file_size
        
        if file_size == 0:
            validation_result["valid"] = False
            validation_result["reason"] = "File is empty"
            return validation_result
            
        # Check if file should be skipped
        if should_skip_file(html_file.name):
            validation_result["valid"] = False
            validation_result["reason"] = "File marked for skipping"
            return validation_result
            
        # Determine file type
        file_type = get_file_type(html_file.name)
        validation_result["file_type"] = file_type
        
        # Try to parse HTML to validate structure
        try:
            soup = parse_html_file(html_file)
            # Basic HTML validation could be added here
        except Exception as e:
            validation_result["valid"] = False
            validation_result["reason"] = f"HTML parsing failed: {e}"
            return validation_result
            
        return validation_result
        
    except Exception as e:
        validation_result["valid"] = False
        validation_result["reason"] = f"Validation error: {e}"
        return validation_result
