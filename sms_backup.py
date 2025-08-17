"""
Google Voice SMS Takeout XML Converter

This script converts Google Voice HTML export files into a standard SMS backup XML format
that can be imported into various SMS backup applications.

The script processes:
- Individual SMS conversations
- Group MMS conversations  
- Images and vCard attachments
- Location sharing pins

Author: [Your Name]
Date: [Date]
"""

import dateutil.parser
import glob
import logging
import os
import phonenumbers
import re
import sys
import time
from datetime import datetime, timedelta
from base64 import b64encode
from bs4 import BeautifulSoup
from io import open  # adds emoji support
from pathlib import Path
from shutil import copyfileobj, move
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from functools import lru_cache

# ====================================================================
# CONFIGURATION CONSTANTS
# ====================================================================

# File paths and names
SMS_BACKUP_FILENAME = "./gvoice-all.xml"
SMS_BACKUP_PATH = Path(SMS_BACKUP_FILENAME)
LOG_FILENAME = 'gvoice_converter.log'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILENAME)
    ]
)
logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.gif'}
SUPPORTED_VCARD_TYPES = {'.vcf'}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_TYPES | SUPPORTED_VCARD_TYPES

# MMS message type constants
MMS_TYPE_SENT = 128
MMS_TYPE_RECEIVED = 132

# Message box constants  
MESSAGE_BOX_SENT = 2
MESSAGE_BOX_RECEIVED = 1

# Participant type codes for MMS
PARTICIPANT_TYPE_SENDER = 137
PARTICIPANT_TYPE_RECEIVER = 151

# Error messages
ERROR_NO_MESSAGES = "No messages found in HTML file"
ERROR_NO_PARTICIPANTS = "Could not find participant phone number"
ERROR_NO_SENDER = "Unable to determine sender in MMS with multiple participants"

# Default values and thresholds
DEFAULT_FALLBACK_TIME = 1000  # milliseconds
MIN_PHONE_NUMBER_LENGTH = 7
FILENAME_TRUNCATE_LENGTH = 50

# MMS placeholder messages
MMS_PLACEHOLDER_MESSAGES = {"MMS Sent", "MMS Received"}

# HTML parsing constants
HTML_PARSER = "html.parser"
GROUP_CONVERSATION_MARKER = "Group Conversation"

class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass

class FileProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass

@dataclass
class ConversionStats:
    """Statistics for the conversion process."""
    num_sms: int = 0
    num_img: int = 0
    num_vcf: int = 0
    own_number: Optional[str] = None

# XML templates for better maintainability
SMS_XML_TEMPLATE = '<sms protocol="0" address="{phone}" date="{time}" type="{type}" subject="null" body="{message}" toa="null" sc_toa="null" service_center="null" read="1" status="1" locked="0" />\n'

MMS_XML_TEMPLATE = '''<mms address="{participants}" ct_t="application/vnd.wap.multipart.related" date="{time}" m_type="{m_type}" msg_box="{msg_box}" read="1" rr="129" seen="1" sim_slot="1" sub_id="-1" text_only="{text_only}">
    <parts>
{text_part}{image_parts}{vcard_parts}  </parts>
    <addrs>
{participants_xml}  </addrs>
</mms>'''

TEXT_PART_TEMPLATE = '    <part ct="text/plain" seq="0" text="{text}"/> \n'
PARTICIPANT_TEMPLATE = '    <addr address="{number}" charset="106" type="{code}"/> \n'
IMAGE_PART_TEMPLATE = '    <part seq="0" ct="image/{type}" name="{name}" chset="null" cd="null" fn="null" cid="&lt;{name}&gt;" cl="{name}" ctt_s="null" ctt_t="null" text="null" data="{data}" />\n'
VCARD_PART_TEMPLATE = '    <part seq="0" ct="text/x-vCard" name="{name}" chset="null" cd="null" fn="null" cid="&lt;{name}&gt;" cl="{name}" ctt_s="null" ctt_t="null" text="null" data="{data}" />\n'

def validate_configuration():
    """Validate that all required configuration constants are properly set."""
    required_constants = {
        'SMS_BACKUP_FILENAME': SMS_BACKUP_FILENAME,
        'SUPPORTED_IMAGE_TYPES': SUPPORTED_IMAGE_TYPES,
        'SUPPORTED_VCARD_TYPES': SUPPORTED_VCARD_TYPES,
        'MMS_TYPE_SENT': MMS_TYPE_SENT,
        'MMS_TYPE_RECEIVED': MMS_TYPE_RECEIVED,
        'MESSAGE_BOX_SENT': MESSAGE_BOX_SENT,
        'MESSAGE_BOX_RECEIVED': MESSAGE_BOX_RECEIVED,
        'PARTICIPANT_TYPE_SENDER': PARTICIPANT_TYPE_SENDER,
        'PARTICIPANT_TYPE_RECEIVER': PARTICIPANT_TYPE_RECEIVER
    }
    
    for name, value in required_constants.items():
        if value is None:
            raise ConfigurationError(f"Required configuration constant {name} is not set")
    
    logger.info("Configuration validation passed")


def main():
    """
    Main function that orchestrates the conversion process.
    
    Processes all HTML files in the current directory and subdirectories,
    converting them to a unified SMS backup XML format.
    """
    try:
        start_time = datetime.now()
        logger.info(f"Starting conversion at {start_time.strftime('%H:%M:%S')}")
        
        # Validate configuration
        validate_configuration()
        
        # Validate and prepare output file
        logger.info("Preparing output file...")
        prepare_output_file()
        
        # Remove problematic files that won't convert properly
        logger.info("Checking for problematic files...")
        remove_problematic_files()
        
        # Build attachment mapping
        logger.info("Building attachment mapping...")
        src_filename_map = build_attachment_mapping()
        logger.info(f"Found {len(src_filename_map)} attachment mappings")
        
        # Process HTML files
        logger.info("Processing HTML files...")
        stats = process_html_files(src_filename_map)
        
        # Finalize output file
        logger.info("Finalizing output file...")
        finalize_output_file(stats['num_sms'])
        
        # Display results
        display_results(start_time, stats)
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise ConversionError(f"Failed to convert SMS data: {e}")


def prepare_output_file():
    """Prepare the output file for writing."""
    try:
        # Ensure directory exists
        SMS_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty file
        with SMS_BACKUP_PATH.open("w") as f:
            pass  # Just create the file
        
        logger.info(f"Output file prepared: {SMS_BACKUP_FILENAME}")
    except Exception as e:
        raise FileProcessingError(f"Failed to prepare output file: {e}")


def build_attachment_mapping() -> Dict[str, str]:
    """Build mapping from HTML src elements to attachment filenames."""
    try:
        src_elements = extract_src(".")
        att_filenames = list_att_filenames(".")
        return src_to_filename_mapping(src_elements, att_filenames)
    except Exception as e:
        logger.warning(f"Failed to build attachment mapping: {e}")
        return {}


def process_html_files(src_filename_map: Dict[str, str]) -> Dict[str, int]:
    """Process all HTML files and return statistics."""
    stats = {'num_sms': 0, 'num_img': 0, 'num_vcf': 0}
    own_number = None

    for html_file in Path(".").rglob("*.html"):
        try:
            file_stats = process_single_html_file(html_file, src_filename_map, own_number)
            
            # Update statistics
            stats['num_sms'] += file_stats['num_sms']
            stats['num_img'] += file_stats['num_img']
            stats['num_vcf'] += file_stats['num_vcf']
            
            # Extract own number from first file if not already found
            if own_number is None:
                own_number = file_stats.get('own_number')
                
        except Exception as e:
            logger.error(f"Failed to process {html_file}: {e}")
                continue

    return stats


def process_single_html_file(html_file: Path, src_filename_map: Dict[str, str], 
                            own_number: Optional[str]) -> Dict[str, Union[int, str]]:
    """Process a single HTML file and return file-specific statistics."""
    logger.info(f"Processing {html_file}")
    
    # Parse HTML file
    soup = parse_html_file(html_file)
            messages_raw = soup.find_all(class_="message")
    
    if not messages_raw:
        logger.warning(f"{ERROR_NO_MESSAGES}: {html_file}")
        return {'num_sms': 0, 'num_img': 0, 'num_vcf': 0}
    
    # Extract own phone number if not already found
    if own_number is None:
        own_number = extract_own_phone_number(soup)
    
    # Determine conversation type and process
    is_group_conversation = GROUP_CONVERSATION_MARKER in html_file.name

            if is_group_conversation:
                participants_raw = soup.find_all(class_="participants")
        write_mms_messages(html_file.name, participants_raw, messages_raw, 
                            own_number, src_filename_map)
            else:
        write_sms_messages(html_file.name, messages_raw, own_number, src_filename_map)
    
    # Count attachments in this file
    num_img = count_attachments_in_file(html_file, SUPPORTED_IMAGE_TYPES)
    num_vcf = count_attachments_in_file(html_file, SUPPORTED_VCARD_TYPES)
    
    return {
        'num_sms': len(messages_raw),
        'num_img': num_img,
        'num_vcf': num_vcf,
        'own_number': own_number
    }


def parse_html_file(html_file: Path) -> BeautifulSoup:
    """Parse HTML file with error handling."""
    try:
        with open(html_file, "r", encoding="utf8") as f:
            return BeautifulSoup(f, HTML_PARSER)
    except Exception as e:
        raise FileProcessingError(f"Failed to parse HTML file {html_file}: {e}")


def count_attachments_in_file(html_file: Path, extensions: set) -> int:
    """Count attachments of specific types in a file's directory."""
    try:
        # Use set intersection for more efficient counting
        file_extensions = {path.suffix.lower() for path in html_file.parent.iterdir() 
                            if path.is_file()}
        return len(file_extensions & extensions)
    except Exception:
        return 0


def finalize_output_file(num_sms: int):
    """Finalize the output file by writing closing tag and header."""
    try:
        # Write closing tag
        with open(SMS_BACKUP_FILENAME, "a", encoding="utf8") as f:
            f.write("</smses>")
        
        # Write header with final count
        write_header(SMS_BACKUP_FILENAME, num_sms)
        logger.info("Output file finalized successfully")
        
    except Exception as e:
        raise FileProcessingError(f"Failed to finalize output file: {e}")


def format_elapsed_time(seconds: int) -> str:
    """Format elapsed time in a human-readable format using timedelta."""
    delta = timedelta(seconds=seconds)
    
    # Use timedelta's built-in attributes for cleaner formatting
    if delta.days > 0:
        return f"{delta.days} days, {delta.seconds // 3600} hours, {(delta.seconds % 3600) // 60} minutes"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours} hours, {minutes} minutes" if minutes > 0 else f"{hours} hours"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        secs = delta.seconds % 60
        return f"{minutes} minutes, {secs} seconds" if secs > 0 else f"{minutes} minutes"
    else:
        return f"{delta.seconds} seconds"


def display_results(start_time: datetime, stats: Union[Dict[str, int], ConversionStats]):
    """Display conversion results and timing information."""
    elapsed_time = datetime.now() - start_time
    time_str = format_elapsed_time(int(elapsed_time.total_seconds()))
    
    # Handle both dict and dataclass formats
    if isinstance(stats, dict):
        # Validate stats dictionary
        expected_keys = {'num_sms', 'num_img', 'num_vcf'}
        if not all(key in stats for key in expected_keys):
            logger.warning("Incomplete statistics - some data may be missing")
        
        num_sms = stats.get('num_sms', 0)
        num_img = stats.get('num_img', 0)
        num_vcf = stats.get('num_vcf', 0)
    else:
        num_sms = stats.num_sms
        num_img = stats.num_img
        num_vcf = stats.num_vcf
    
    logger.info(f"Conversion completed in {time_str}")
    logger.info(f"Processed {num_sms} messages, {num_img} images, and {num_vcf} contact cards")


def extract_own_phone_number(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract the user's own phone number from the HTML.
    
    Args:
        soup: BeautifulSoup object of the HTML file
        
    Returns:
        str: The user's phone number in E164 format, or None if not found
    """
    for abbr_tag in soup.find_all('abbr', class_='fn'):
        if abbr_tag.get_text(strip=True) == "Me":
            a_tag = abbr_tag.find_previous('a', class_='tel')
            if a_tag:
                phone_number = a_tag.get('href').split(':', 1)[-1]
                try:
                    parsed_number = phonenumbers.parse(phone_number, None)
                    return format_number(parsed_number)
                except phonenumbers.phonenumberutil.NumberParseException:
                    return phone_number
    return None


def remove_problematic_files():
    """
    Remove conversation files that won't convert properly.
    
    This includes conversations without phone numbers, shortcode numbers,
    and other non-SMS content like missed calls and voicemails.
    """
    try:
    user_confirmation = input("""\

    Would you like to automatically remove conversations that won't convert?
    This is conversations without attached phone numbers, ones with shortcode phone numbers,
    or things like missed calls and voicemails.
    If you say yes, this will automatically delete those files before converting.
    (Y/n)? """)
        
        if user_confirmation.lower() not in ['', 'y', 'yes']:
            logger.info("Skipping problematic file removal")
            return
        
        logger.info("Removing problematic files...")
        
        # Remove files without phone numbers
        remove_files_by_pattern("Calls/ -*", "no phone number")
        
        # Remove files with shortcode numbers (1-8 digits)
        remove_files_by_pattern("Calls/*", "shortcode", r'^[0-9]{1,8}.*$')
        
        logger.info("Problematic file removal completed")
        
    except Exception as e:
        logger.error(f"Failed to remove problematic files: {e}")


def remove_files_by_pattern(directory_pattern: str, description: str, 
                            filename_pattern: Optional[str] = None):
    """Remove files matching a pattern with error handling."""
    try:
        files_to_remove = glob.glob(directory_pattern)
        
        for file_path in files_to_remove:
            # Additional filename filtering if pattern provided
            if filename_pattern and not re.match(filename_pattern, Path(file_path).name):
                continue
                
            try:
                os.remove(file_path)
                logger.info(f"Removed {description} conversation: {file_path}")
                except OSError as e:
                logger.warning(f"Failed to remove {description} conversation {file_path}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to process {description} files: {e}")


def escape_xml(s: str) -> str:
    """
    Escape special characters for XML output.
    
    Args:
        s: String to escape
        
    Returns:
        str: XML-escaped string
    """
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&apos;",
        '"': "&quot;"
    }
    
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s


def extract_src(html_directory: str) -> List[str]:
    """
    Extract image src attributes and vCard href attributes from HTML files.
    
    Args:
        html_directory: Directory to search for HTML files
        
    Returns:
        list: List of src/href values found in HTML files
    """
    src_list = []
    
    try:
        for html_file in Path(html_directory).rglob('*.html'):
            try:
        with open(html_file, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file, HTML_PARSER)
                    
                    # Extract image src attributes
                    src_list.extend(
                        img['src'] for img in soup.find_all('img') 
                        if 'src' in img.attrs
                    )
                    
                    # Extract vCard href attributes
                    src_list.extend(
                        a['href'] for a in soup.find_all('a', class_='vcard') 
                        if 'href' in a.attrs
                    )
                    
            except Exception as e:
                logger.warning(f"Failed to process {html_file}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Failed to extract src from {html_directory}: {e}")
    
    return src_list


def list_att_filenames(directory: str) -> List[str]:
    """
    List all attachment filenames with supported extensions.
    
    Args:
        directory: Directory to search for attachments
        
    Returns:
        list: List of attachment filenames
    """
    try:
        return [
            str(path.name) for path in Path(directory).rglob('*') 
            if path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    except Exception as e:
        logger.error(f"Failed to list attachment filenames from {directory}: {e}")
        return []


@lru_cache(maxsize=1000)
def normalize_filename(filename: str) -> str:
    """
    Remove file extension and parenthesized numbers from filename.
    
    This is used to match filenames back to their respective img_src keys.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Normalized filename (max 50 characters)
    """
    # Remove extension and parenthesized numbers, truncate at 50 characters
    return re.sub(r'(?:\((\d+)\))?\.(jpg|gif|png|vcf)$', '', filename)[:FILENAME_TRUNCATE_LENGTH]


def custom_filename_sort(filename: str) -> Tuple[str, int, str]:
    """
    Custom sorting function for filenames with parenthesized numbers.
    
    Ensures files with parenthesized numbers follow the base filename.
    
    Args:
        filename: Filename to sort
        
    Returns:
        tuple: (base_filename, number, extension) for sorting
    """
    match = re.match(r'(.*?)(?:\((\d+)\))?(\.\w+)?$', filename)
    if match:
        base_filename = match.group(1)
        number = int(match.group(2)) if match.group(2) else -1
        extension = match.group(3) if match.group(3) else ''
        return (base_filename, number, extension)
        return (filename, float('inf'), '')


def src_to_filename_mapping(src_elements: List[str], att_filenames: List[str]) -> Dict[str, str]:
    """
    Create a mapping from HTML src elements to attachment filenames.
    
    Args:
        src_elements: List of src/href values from HTML
        att_filenames: List of attachment filenames
        
    Returns:
        dict: Mapping from src to filename
    """
    used_filenames = set()
    mapping = {}
    
    # Sort filenames before matching to ensure consistent results
    att_filenames.sort(key=custom_filename_sort)
    
    for src in src_elements:
        assigned_filename = None
        for filename in att_filenames:
            normalized_filename = normalize_filename(filename)
            if normalized_filename in src and filename not in used_filenames:
                assigned_filename = filename
                used_filenames.add(filename)
                break
        mapping[src] = assigned_filename or 'No unused match found'
    
    return mapping


def write_sms_messages(file: str, messages_raw: List, own_number: Optional[str], 
                        src_filename_map: Dict[str, str]):
    """
    Write SMS messages to the backup file.
    
    Args:
        file: HTML filename being processed
        messages_raw: List of message elements from HTML
        own_number: User's phone number
        src_filename_map: Mapping of src elements to filenames
    """
    try:
        fallback_number = extract_fallback_number(file)
        
        # Get the primary phone number for this conversation
    phone_number, participant_raw = get_first_phone_number(
        messages_raw, fallback_number
    )

        # Search for fallback numbers in similarly named files if needed
    if phone_number == 0:
            phone_number = search_fallback_numbers(file, fallback_number)

        sms_values = {"phone": phone_number}

        # Write SMS messages to backup file
        with open(SMS_BACKUP_FILENAME, "a", encoding="utf8") as sms_backup_file:
            for message in messages_raw:
                try:
                    # Check if message contains images or vCards (treat as MMS)
                    if (message.find_all("img") or 
                        message.find_all("a", class_='vcard')):
                        write_mms_messages(file, [[participant_raw]], [message], 
                                        own_number, src_filename_map)
                        continue
                    
                    # Skip MMS placeholder messages
                    message_content = get_message_text(message)
                    if message_content in MMS_PLACEHOLDER_MESSAGES:
                        continue
                    
                    # Prepare SMS message data
                    sms_values.update({
                        "type": get_message_type(message),
                        "message": message_content,
                        "time": get_time_unix(message)
                    })
                    
                    # Format SMS XML
                    sms_text = format_sms_xml(sms_values)
                    sms_backup_file.write(sms_text)
                    
                except Exception as e:
                    logger.warning(f"Failed to process SMS message: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Failed to write SMS messages for {file}: {e}")


def extract_fallback_number(file: str) -> Union[str, int]:
    """Extract fallback phone number from filename."""
    match = re.search(r"(^\+[0-9]+)", Path(file).name)
    return match.group() if match else 0


def format_sms_xml(sms_values: Dict[str, Union[str, int]]) -> str:
    """Format SMS message as XML using template."""
    return SMS_XML_TEMPLATE.format(**sms_values)


def search_fallback_numbers(file: str, fallback_number: Union[str, int]) -> Union[str, int]:
    """
    Search for fallback phone numbers in related files.
    
    Args:
        file: Current HTML filename
        fallback_number: Initial fallback number
        
    Returns:
        str: Found phone number or 0 if none found
    """
    search_patterns = [
        # Search in similarly named files
        ("-".join(Path(file).stem.split("-")[0:1]) + "*.html", "message"),
        # Search in Placed/Received files
        (f'{Path(file).stem.split("-")[0]}- *.html', "contributor vcard")
    ]
    
    try:
        for pattern, search_type in search_patterns:
            phone_number = search_files_for_phone_number(pattern, search_type, file)
            if phone_number != 0:
                return phone_number
                
    except Exception as e:
        logger.warning(f"Failed to search fallback numbers for {file}: {e}")
    
    return 0


def search_files_for_phone_number(pattern: str, search_type: str, original_file: str) -> Union[str, int]:
    """Search files matching a pattern for phone numbers."""
    try:
        for fallback_file in Path.cwd().glob(f"**/{pattern}"):
            try:
            with fallback_file.open("r", encoding="utf8") as ff:
                    soup = BeautifulSoup(ff, HTML_PARSER)
                    
                    if search_type == "message":
                        messages_raw = soup.find_all(class_="message")
                        phone_number, _ = get_first_phone_number(messages_raw, 0)
                        if phone_number != 0:
                            return phone_number
                            
                    elif search_type == "contributor vcard":
            contrib_vcards = soup.find_all(class_="contributor vcard")
            for contrib_vcard in contrib_vcards:
                            if contrib_vcard.a and "href" in contrib_vcard.a.attrs:
                phone_number_ff = contrib_vcard.a["href"][4:]
                                if phone_number_ff:
                                    phone_number, _ = get_first_phone_number([], phone_number_ff)
            if phone_number != 0:
                                        return phone_number
                                    
            except Exception as e:
                logger.warning(f"Failed to search fallback file {fallback_file}: {e}")
                continue
                
    except Exception as e:
        logger.warning(f"Failed to search pattern {pattern}: {e}")
    
    return 0


def write_mms_messages(file: str, participants_raw: List, messages_raw: List, 
                        own_number: Optional[str], src_filename_map: Dict[str, str]):
    """
    Write MMS messages to the backup file.
    
    Args:
        file: HTML filename being processed
        participants_raw: List of participant elements
        messages_raw: List of message elements
        own_number: User's phone number
        src_filename_map: Mapping of src elements to filenames
    """
    try:
        with open(SMS_BACKUP_FILENAME, "a", encoding="utf8") as sms_backup_file:
            # Extract participant phone numbers
    participants = get_participant_phone_numbers(participants_raw)
    participants_text = "~".join(participants)

            # Add own number to participants if not already present
            if own_number and own_number not in participants:
                participants.append(own_number)
    
    for message in messages_raw:
                try:
                    # Determine sender and message type
        sender = get_mms_sender(message, participants)
                    sent_by_me = sender == own_number
        
                    # Handle images and vCards
        images = message.find_all("img")
        vcards = message.find_all("a", class_='vcard')
                    
                    # Process attachments using consolidated function
                    image_parts, extracted_url = process_attachments(images, file, src_filename_map, 'image')
                    vcard_parts, vcard_url = process_attachments(vcards, file, src_filename_map, 'vcard')
                    
                    # Use vCard URL if available, otherwise use image URL
                    final_url = vcard_url or extracted_url
                    
                    # Determine if this is a text-only message
                    text_only = 1 if not (images or vcards) else 0
                    
                    # Get message text (handle location pins specially)
                    if final_url:
                        message_text = "Dropped pin&#10;" + final_url
                else:
                        message_text = get_message_text(message)
                    
                    # Skip MMS placeholder messages
                    if message_text in MMS_PLACEHOLDER_MESSAGES:
                        continue
                    
                    # Get message timestamp
                    message_time = get_time_unix(message)
                    
                    # Build participant XML
                    participants_xml = build_participants_xml(participants, sender, sent_by_me)
                    
                    # Determine message box and type
                    msg_box = MESSAGE_BOX_SENT if sent_by_me else MESSAGE_BOX_RECEIVED
                    m_type = MMS_TYPE_SENT if sent_by_me else MMS_TYPE_RECEIVED
                    
                    # Build MMS XML
                    mms_text = build_mms_xml(
                        participants_text, message_time, m_type, msg_box, text_only,
                        message_text, image_parts, vcard_parts, participants_xml
                    )
                    
                    sms_backup_file.write(mms_text)
                    
                except Exception as e:
                    logger.warning(f"Failed to process MMS message: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Failed to write MMS messages for {file}: {e}")


def process_attachments(attachments: List, file: str, src_filename_map: Dict[str, str], 
                        attachment_type: str) -> Tuple[str, str]:
    """
    Generic function to process attachments (images or vCards).
    
    Args:
        attachments: List of attachment elements
        file: HTML filename
        src_filename_map: Mapping of src elements to filenames
        attachment_type: Type of attachment ('image' or 'vcard')
        
    Returns:
        tuple: (xml_parts, extracted_url)
    """
    if not attachments:
        return "", ""
    
    xml_parts = []
    extracted_url = ""
    
    for attachment in attachments:
        try:
            xml_part, url = process_single_attachment(attachment, file, src_filename_map, attachment_type)
            if xml_part:
                xml_parts.append(xml_part)
            if url:
                extracted_url = url
        except Exception as e:
            src = attachment.get('src' if attachment_type == 'image' else 'href', 'unknown')
            logger.warning(f"Failed to process {attachment_type} {src}: {e}")
            continue
    
    return "".join(xml_parts), extracted_url


def process_single_attachment(attachment, file: str, src_filename_map: Dict[str, str], 
                            attachment_type: str) -> Tuple[Optional[str], str]:
    """Process a single attachment and return XML part and extracted URL."""
    src_attr = 'src' if attachment_type == 'image' else 'href'
    src = attachment.get(src_attr)
    if not src:
        return None, ""
    
    # Find matching file
    supported_types = SUPPORTED_IMAGE_TYPES if attachment_type == 'image' else SUPPORTED_VCARD_TYPES
    file_path = find_attachment_file(src, file, src_filename_map, supported_types)
    if not file_path:
        return None, ""
    
    try:
        if attachment_type == 'vcard':
            # Check if this is a location sharing vCard
            extracted_url = extract_location_url(file_path)
            if extracted_url:
                return None, extracted_url
        
        # Process as regular attachment
        attachment_data = encode_file_content(file_path)
        relative_path = file_path.relative_to(Path.cwd())
        
        if attachment_type == 'image':
            image_type = get_image_type(file_path)
            return build_attachment_xml_part(relative_path, f"image/{image_type}", attachment_data, IMAGE_PART_TEMPLATE), ""
                else:
            return build_attachment_xml_part(relative_path, "text/x-vCard", attachment_data, VCARD_PART_TEMPLATE), ""
        
    except Exception as e:
        logger.error(f"Failed to process {attachment_type} {file_path}: {e}")
        return None, ""


def build_attachment_xml_part(relative_path: Path, content_type: str, data: str, template: str) -> str:
    """Build XML part for any attachment using the provided template."""
    return template.format(
        type=content_type.split('/')[-1] if content_type.startswith('image/') else content_type,
        name=relative_path,
        data=data
    )


def find_attachment_file(src: str, file: str, src_filename_map: Dict[str, str], 
                        supported_types: set) -> Optional[Path]:
    """Find attachment file using mapping or fallback logic."""
    # Try to find matching file using the mapping
    filename = src_filename_map.get(src)
    
    if filename and filename != "No unused match found":
        # Use the mapped filename
        filename_pattern = f"**/*{filename}"
    else:
        # Fallback: construct filename from HTML filename and src
        html_prefix = file.split('-', 1)[0]
        constructed_filename = html_prefix + src[src.find('-'):]
        filename_pattern = f"**/{constructed_filename}.*"
    
    # Find and filter paths
    paths = [p for p in Path.cwd().glob(filename_pattern) 
            if p.is_file() and p.suffix.lower() in supported_types]
    
    # Validate results
    if not paths:
        logger.warning(f"No matching files found for src: {src}")
        return None
    if len(paths) > 1:
        logger.warning(f"Multiple matching files found for src {src}: {paths}")
    
    return paths[0]


def get_image_type(image_path: Path) -> str:
    """Get MIME type for image file."""
    return "jpeg" if image_path.suffix.lower() == ".jpg" else image_path.suffix[1:]


def encode_file_content(file_path: Path) -> str:
    """Encode file content as base64 string."""
    return b64encode(file_path.read_bytes()).decode('utf-8')


def extract_location_url(vcard_path: Path) -> str:
    """Extract location URL from vCard if it's a location sharing card."""
    try:
        with vcard_path.open("r", encoding="utf-8") as f:
                    current_location_found = False
            for line in f:
                        if line.startswith("FN:") and "Current Location" in line:
                            current_location_found = True
                        if current_location_found and line.startswith("URL;type=pref:"):
                    url = line.split(":", 1)[1].strip()
                    return escape_xml(url.replace("\\", ""))
        return ""
    except Exception as e:
        logger.warning(f"Failed to extract location URL from {vcard_path}: {e}")
        return ""


def build_participants_xml(participants: List[str], sender: str, sent_by_me: bool) -> str:
    """
    Build XML for MMS participants.
    
    Args:
        participants: List of participant phone numbers
        sender: Sender's phone number
        sent_by_me: Whether the message was sent by the user
        
    Returns:
        str: XML string for participants
    """
    return "".join(
        PARTICIPANT_TEMPLATE.format(
            number=participant,
            code=PARTICIPANT_TYPE_SENDER if (participant == sender or 
                                            (sent_by_me and participant == "Me")) 
                  else PARTICIPANT_TYPE_RECEIVER
        )
        for participant in participants
    )


def build_mms_xml(participants_text: str, message_time: int, m_type: int, msg_box: int, 
                    text_only: int, message_text: str, image_parts: str, vcard_parts: str, 
                    participants_xml: str) -> str:
    """
    Build complete MMS XML message.
    
    Args:
        participants_text: Semicolon-separated participant list
        message_time: Message timestamp
        m_type: MMS message type
        msg_box: Message box type
        text_only: Whether message contains only text
        message_text: Message text content
        image_parts: XML for image parts
        vcard_parts: XML for vCard parts
        participants_xml: XML for participants
        
    Returns:
        str: Complete MMS XML message
    """
    # Build text part if not an MMS placeholder
    text_part = TEXT_PART_TEMPLATE.format(text=message_text) if message_text not in MMS_PLACEHOLDER_MESSAGES else ""
    
    return MMS_XML_TEMPLATE.format(
        participants=participants_text,
        time=message_time,
        m_type=m_type,
        msg_box=msg_box,
        text_only=text_only,
        text_part=text_part,
        image_parts=image_parts,
        vcard_parts=vcard_parts,
        participants_xml=participants_xml
    )


def get_message_type(message: BeautifulSoup) -> int:
    """
    Determine if a message was sent (2) or received (1).
    
    Args:
        message: Message element from HTML
        
    Returns:
        int: Message type (1=received, 2=sent)
    """
    try:
    author_raw = message.cite
        return 2 if not author_raw.span else 1  # 2=sent, 1=received
    except Exception as e:
        logger.warning(f"Failed to determine message type: {e}")
        return 1  # Default to received


def get_message_text(message: BeautifulSoup) -> str:
    """
    Extract and clean message text from HTML.
    
    Args:
        message: Message element from HTML
        
    Returns:
        str: Cleaned message text
    """
    try:
        # Extract text from <q> tag and clean HTML entities
        q_tag = message.find("q")
        if not q_tag:
            return ""
            
        message_text = str(q_tag).strip()[3:-4]
        
        # Replace HTML elements with XML entities using a mapping
        html_replacements = {
            "<br/>": "&#10;",
            "'": "&apos;",
            '"': "&quot;",
            "<": "&lt;",
            ">": "&gt;"
        }
        
        for old, new in html_replacements.items():
            message_text = message_text.replace(old, new)

    return message_text

    except Exception as e:
        logger.warning(f"Failed to extract message text: {e}")
        return ""


def get_mms_sender(message: BeautifulSoup, participants: List[str]) -> str:
    """
    Determine the sender of an MMS message.
    
    Args:
        message: Message element from HTML
        participants: List of participant phone numbers
        
    Returns:
        str: Sender's phone number
        
    Raises:
        ConversionError: If sender cannot be determined
    """
    try:
        cite_element = message.cite
        if not cite_element or not cite_element.a:
            raise ConversionError("Message cite element or anchor not found")
            
        number_text = cite_element.a.get("href", "")[4:]
        
        if number_text:
            try:
                return format_number(phonenumbers.parse(number_text, None))
            except phonenumbers.phonenumberutil.NumberParseException as e:
                logger.warning(f"Failed to parse phone number {number_text}: {e}")
                return number_text
        
        # If no href, assume single participant
        if len(participants) != 1:
            raise ConversionError(ERROR_NO_SENDER)
        return participants[0]
            
    except Exception as e:
        if isinstance(e, ConversionError):
            raise
        raise ConversionError(f"Failed to determine MMS sender: {e}")


def get_first_phone_number(messages: List, fallback_number: Union[str, int]) -> Tuple[Union[str, int], BeautifulSoup]:
    """
    Extract the first valid phone number from messages.
    
    Args:
        messages: List of message elements
        fallback_number: Fallback number from filename
        
    Returns:
        tuple: (phone_number, participant_data)
    """
    # Look for phone numbers in message authors
    for author_raw in messages:
        try:
        if not author_raw.span:
            continue

        sender_data = author_raw.cite
            if not sender_data or not sender_data.a:
                continue
                
            # Skip if first number is "Me"
        if sender_data.text == "Me":
            continue
                
            phonenumber_text = sender_data.a.get("href", "")[4:]
            if not phonenumber_text:
            continue

        try:
            phone_number = phonenumbers.parse(phonenumber_text, None)
                return format_number(phone_number), sender_data
        except phonenumbers.phonenumberutil.NumberParseException:
            return phonenumber_text, sender_data

        except Exception as e:
            logger.warning(f"Failed to process message author: {e}")
            continue

    # Fallback: use number from filename
    if fallback_number and len(str(fallback_number)) >= MIN_PHONE_NUMBER_LENGTH:
        try:
            fallback_number = format_number(phonenumbers.parse(str(fallback_number), None))
        except phonenumbers.phonenumberutil.NumberParseException:
            pass
    
    # Create dummy participant data for fallback
    return fallback_number, create_dummy_participant(fallback_number)


def create_dummy_participant(phone_number: Union[str, int]) -> BeautifulSoup:
    """Create dummy participant data for fallback phone numbers."""
    try:
        html_content = f'<cite class="sender vcard"><a class="tel" href="tel:{phone_number}"><abbr class="fn" title="">Unknown</abbr></a></cite>'
        return BeautifulSoup(html_content, features="html.parser")
    except Exception as e:
        logger.warning(f"Failed to create dummy participant: {e}")
        return BeautifulSoup('<cite></cite>', features="html.parser")


def get_participant_phone_numbers(participants_raw: List) -> List[str]:
    """
    Extract phone numbers from participant elements.
    
    Args:
        participants_raw: List of participant elements from HTML
        
    Returns:
        list: List of formatted phone numbers
        
    Raises:
        ConversionError: If participant phone number cannot be found
    """
    participants = []

    try:
    for participant_set in participants_raw:
        for participant in participant_set:
                try:
                    if not hasattr(participant, "a") or not participant.a:
                continue

                    phone_number_text = participant.a.get("href", "")[4:]
                    
                    # Validate phone number
                    if not phone_number_text or phone_number_text == "0":
                        raise ConversionError(ERROR_NO_PARTICIPANTS)
                    
                    try:
                        participants.append(format_number(phonenumbers.parse(phone_number_text, None)))
            except phonenumbers.phonenumberutil.NumberParseException:
                participants.append(phone_number_text)
                        
                except Exception as e:
                    if isinstance(e, ConversionError):
                        raise
                    logger.warning(f"Failed to process participant: {e}")
                    continue
                    
    except Exception as e:
        if isinstance(e, ConversionError):
            raise
        raise ConversionError(f"Failed to extract participant phone numbers: {e}")

    return participants


def format_number(phone_number: phonenumbers.PhoneNumber) -> str:
    """
    Format phone number to E164 standard.
    
    Args:
        phone_number: PhoneNumber object from phonenumbers library
        
    Returns:
        str: E164 formatted phone number
    """
    try:
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        logger.warning(f"Failed to format phone number: {e}")
        return str(phone_number)


def get_time_unix(message: BeautifulSoup) -> int:
    """
    Extract and convert message timestamp to Unix milliseconds.
    
    Args:
        message: Message element from HTML
        
    Returns:
        int: Unix timestamp in milliseconds
    """
    try:
    time_raw = message.find(class_="dt")
        if not time_raw or "title" not in time_raw.attrs:
            raise ConversionError("Message timestamp element not found")
            
    ymdhms = time_raw["title"]
    time_obj = dateutil.parser.isoparse(ymdhms)
        
        # Convert to Unix milliseconds (including microseconds)
        return int(time.mktime(time_obj.timetuple()) * 1000 + time_obj.microsecond // 1000)
        
    except Exception as e:
        logger.error(f"Failed to extract message timestamp: {e}")
        return int(time.time() * DEFAULT_FALLBACK_TIME)  # Return current time as fallback


def write_header(filename: str, numsms: int):
    """
    Write XML header to the beginning of the backup file.
    
    Uses a memory-efficient approach by creating a temporary file
    and then moving it to replace the original.
    
    Args:
        filename: Output filename
        numsms: Total number of SMS messages
    """
    try:
        # Create temporary file with header
    with NamedTemporaryFile(dir=Path.cwd(), delete=False) as backup_temp:
            # Write header using template
            header_lines = [
                "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
                "<!--Converted from GV Takeout data -->",
                f'<smses count="{numsms}">'
            ]
            
            backup_temp.write(bytes("\n".join(header_lines) + "\n", encoding="utf8"))
            
            # Copy original file content after header
        with open(filename, "rb") as backup_file:
            copyfileobj(backup_file, backup_temp)
        
            # Replace original file with temp file
    move(backup_temp.name, filename)
            logger.info(f"Header written successfully for {numsms} messages")
        
    except Exception as e:
        raise FileProcessingError(f"Failed to write header: {e}")


if __name__ == "__main__":
    try:
main()
    except KeyboardInterrupt:
        logger.info("Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        sys.exit(1)
