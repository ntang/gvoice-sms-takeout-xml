"""
File Type Processor Module for SMS/MMS conversion.

This module handles the processing of different types of HTML files (SMS, MMS, calls, voicemails)
and coordinates the extraction and processing of their content.
"""

import logging
from pathlib import Path
from typing import Dict, Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.processing_context import ProcessingContext
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
    config: Optional["ProcessingConfig"] = None,
    context: Optional["ProcessingContext"] = None,
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
                config=config,
                context=context,
            )
        elif file_type == "call":
            return process_call_file(
                html_file,
                soup,
                own_number,
                src_filename_map,
                conversation_manager,
                phone_lookup_manager,
                config=config,
            )
        elif file_type == "voicemail":
            return process_voicemail_file(
                html_file,
                soup,
                own_number,
                src_filename_map,
                conversation_manager,
                phone_lookup_manager,
                config=config,
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

    except TypeError as e:
        # CRITICAL: This indicates a function signature mismatch - a code bug
        logger.error(f"🚨 CRITICAL BUG - Function signature mismatch for {html_file.name}: {e}")
        logger.error("This is a code defect that must be fixed immediately")
        logger.error(f"File type: {file_type}, attempting to call: process_{file_type}_file")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise  # Don't hide this - it's a programming error that needs attention
        
    except (OSError, IOError) as e:
        # File system errors - recoverable, continue processing other files
        logger.error(f"File system error processing {html_file.name}: {e}")
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "own_number": own_number,
        }
        
    except Exception as e:
        # Other unexpected errors - log with details but continue processing
        logger.error(f"Unexpected error processing {html_file.name}: {e}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
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
    config: Optional["ProcessingConfig"] = None,
    context: Optional["ProcessingContext"] = None,
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
        config=config,
        context=context,
    )


def process_call_file(
    html_file: Path,
    soup: BeautifulSoup,
    own_number: Optional[str],
    src_filename_map: Dict[str, str],
    conversation_manager: ConversationManager,
    phone_lookup_manager: PhoneLookupManager,
    config: Optional["ProcessingConfig"] = None,
) -> Dict[str, Union[int, str]]:
    """
    Process call files by extracting call info and writing to conversation files.
    """
    # Import the actual functions from sms.py
    from sms import extract_call_info, write_call_entry
    from utils.enhanced_logging import get_metrics_collector
    
    # Start metrics collection for this call file
    file_id = html_file.name
    metrics_collector = get_metrics_collector()
    processing_metrics = metrics_collector.start_processing(file_id, file_format="call")

    # Extract call information
    call_info = extract_call_info(str(html_file), soup)

    # If call info was extracted, write it to conversation files
    if call_info:
        # Write call entry to conversation file using passed managers
        write_call_entry(
            str(html_file),
            call_info,
            own_number,
            soup=soup,
            conversation_manager=conversation_manager,
            phone_lookup_manager=phone_lookup_manager,
            config=config  # Pass config for content tracking and date filtering
        )
        
        # Update metrics
        processing_metrics.messages_processed = 1  # One call processed
        processing_metrics.mark_success()
        
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 1,
            "num_voicemails": 0,
            "own_number": own_number,
        }
    else:
        # No call info extracted
        processing_metrics.mark_failure("No call information found in file")
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
    config: Optional["ProcessingConfig"] = None,
) -> Dict[str, Union[int, str]]:
    """
    Process voicemail files by extracting voicemail info and writing to conversation files.
    """
    # Import the actual functions from sms.py
    from sms import extract_voicemail_info, write_voicemail_entry
    from utils.enhanced_logging import get_metrics_collector
    
    # Start metrics collection for this voicemail file
    file_id = html_file.name
    metrics_collector = get_metrics_collector()
    processing_metrics = metrics_collector.start_processing(file_id, file_format="voicemail")

    # Extract voicemail information
    voicemail_info = extract_voicemail_info(str(html_file), soup)

    # If voicemail info was extracted, write it to conversation files
    if voicemail_info:
        # Write voicemail entry to conversation file using passed managers
        write_voicemail_entry(
            str(html_file), 
            voicemail_info, 
            own_number, 
            soup=soup,
            conversation_manager=conversation_manager,
            phone_lookup_manager=phone_lookup_manager,
            config=config  # Pass config for content tracking and date filtering
        )
        
        # Update metrics
        processing_metrics.messages_processed = 1  # One voicemail processed
        processing_metrics.mark_success()
        
        return {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 1,
            "own_number": own_number,
        }
    else:
        # No voicemail info extracted
        processing_metrics.mark_failure("No voicemail information found in file")
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
