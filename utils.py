"""
Utility functions for SMS/MMS processing.

This module contains common utility functions used throughout the SMS/MMS conversion process.
"""

import logging
import re
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
from datetime import datetime
import phonenumbers

logger = logging.getLogger(__name__)


def extract_phone_numbers_from_text(text: str) -> List[str]:
    """
    Extract phone numbers from text content.
    
    Args:
        text: Text content to search for phone numbers
        
    Returns:
        List of found phone numbers
    """
    import re
    
    # Pattern to match phone numbers in various formats
    phone_patterns = [
        r'tel:(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',  # tel:+1234567890
        r'(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',     # +1234567890
        r'(\+?\d{10,15})',                                          # Basic 10-15 digit numbers
    ]
    
    phone_numbers = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        phone_numbers.extend(matches)
    
    # Remove duplicates while preserving order
    unique_numbers = []
    seen = set()
    for number in phone_numbers:
        if number not in seen:
            unique_numbers.append(number)
            seen.add(number)
    
    return unique_numbers


def is_valid_phone_number(phone_number, filter_non_phone: bool = False) -> bool:
    """
    Check if a phone number is valid with enhanced validation.
    
    Args:
        phone_number: Phone number string or integer to validate
        filter_non_phone: If True, filter out shortcodes and other non-phone patterns
        
    Returns:
        bool: True if phone number appears valid, False otherwise
    """
    if not phone_number:
        return False
    
    # Convert to string if it's an integer or other type
    if not isinstance(phone_number, str):
        phone_number = str(phone_number)
    
    # Clean the phone number
    cleaned = phone_number.strip()
    if not cleaned:
        return False
    
    # Skip if it's a fallback conversation ID
    if cleaned.startswith('unknown_'):
        return False
    
    # Handle hash-based fallback numbers (6-8 digits) for conversation management
    # These are generated when no real phone number is found but we need a conversation identifier
    # Must be exactly 6-8 digits, no more, no less
    # Only accept these if they're not too long and not too short
    if re.match(r'^[0-9]+$', cleaned) and 6 <= len(cleaned) <= 8:
        # This is a hash-based fallback number, accept it for conversation purposes
        return True
    
    # Handle names FIRST (allow them as valid "phone numbers" for conversation purposes)
    # But be more strict - names should have spaces (not just random letters)
    if re.match(r'^[A-Za-z\s\-\.]+$', cleaned) and len(cleaned.strip()) > 2:
        # Names should have spaces to be considered valid
        if ' ' in cleaned:
            return True
    
    # Skip if it's clearly not a phone number (contains letters, etc.)
    # But only after we've checked for valid names
    if re.search(r'[a-zA-Z]', cleaned):
        return False
    
    # Enhanced filtering for non-phone numbers when enabled
    if filter_non_phone:
        # Filter out toll-free numbers (800, 877, 888, 866, 855, 844, 833, 822, 800, 888, 877, 866, 855, 844, 833, 822)
        toll_free_patterns = [
            r'^\+?1?8[0-9]{2}',  # 800, 801, 802, 803, 804, 805, 806, 807, 808, 809
            r'^\+?1?8[7-9][0-9]',  # 870-899 (covers 877, 888, 866, 855, 844, 833, 822)
        ]
        
        for pattern in toll_free_patterns:
            if re.match(pattern, cleaned):
                return False
        
        # Filter out non-US numbers (don't start with +1 or 1)
        if not re.match(r'^\+?1', cleaned):
            return False
    
    # Try the strict phonenumbers library validation first
    try:
        parsed = phonenumbers.parse(cleaned, None)
        if phonenumbers.is_valid_number(parsed):
            return True
    except Exception:
        pass
    
    # Fallback validation for edge cases
    # Check for common phone number patterns - be more strict
    phone_patterns = [
        r'^\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$',  # US format: +1 (555) 123-4567
        r'^\+[0-9]{7,15}$',  # International format: must start with +
    ]
    
    for pattern in phone_patterns:
        if re.match(pattern, cleaned):
            return True
    
    # If it looks like a phone number but failed strict validation,
    # be more strict about what we accept
    if re.match(r'^\+?[0-9\s\-\(\)\.]+$', cleaned):
        # Remove all non-digits and check length
        digits_only = re.sub(r'[^0-9]', '', cleaned)
        
        # Reject numbers that are too long (more than 15 digits is not a valid phone number)
        if len(digits_only) > 15:
            return False
            
        # Must be at least 10 digits for US numbers, 7 for international
        if len(digits_only) >= 10:
            # Must start with +1 for US numbers or have proper international format
            if cleaned.startswith('+1') or cleaned.startswith('1') or cleaned.startswith('+'):
                return True
        elif len(digits_only) >= 7:
            # International numbers must start with +
            if cleaned.startswith('+'):
                return True
    
    return False





def normalize_phone_number(phone_number: str) -> str:
    """Normalize a phone number to E.164 format."""
    try:
        # Parse the phone number
        parsed = phonenumbers.parse(phone_number, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        else:
            return phone_number
    except Exception:
        return phone_number


def extract_phone_numbers_from_text(text: str) -> List[str]:
    """Extract phone numbers from text using regex patterns."""
    # Pattern for various phone number formats
    patterns = [
        r'\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',  # US format
        r'\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}',  # International
        r'tel:([+\d\s\-\(\)]+)',  # tel: links
    ]
    
    phone_numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                # Join tuple matches
                phone = ''.join(match)
            else:
                phone = match
            if phone and len(phone) >= 7:  # Minimum length for a phone number
                phone_numbers.append(phone)
    
    return list(set(phone_numbers))  # Remove duplicates


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"
    return sanitized


def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """Parse timestamp from filename using common patterns."""
    try:
        # Common timestamp patterns in filenames
        patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}Z)',  # 2024-01-01T12_00_00Z
            r'(\d{4}-\d{2}-\d{2})',  # 2024-01-01
            r'(\d{8})',  # 20240101
            r'(\d{4}_\d{2}_\d{2})',  # 2024_01_01
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                timestamp_str = match.group(1)
                
                # Parse based on pattern
                if 'T' in timestamp_str and 'Z' in timestamp_str:
                    # Format: 2024-01-01T12_00_00Z
                    timestamp_str = timestamp_str.replace('_', ':')
                    return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
                elif '-' in timestamp_str:
                    # Format: 2024-01-01
                    return datetime.strptime(timestamp_str, '%Y-%m-%d')
                elif '_' in timestamp_str:
                    # Format: 2024_01_01
                    return datetime.strptime(timestamp_str, '%Y_%m_%d')
                else:
                    # Format: 20240101
                    return datetime.strptime(timestamp_str, '%Y%m%d')
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to parse timestamp from filename '{filename}': {e}")
        return None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    if isinstance(directory, str):
        directory = Path(directory)
    
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_file_extension(file_path: Union[str, Path]) -> str:
    """Get the file extension from a file path."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    return file_path.suffix.lower()


def is_html_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is an HTML file."""
    return get_file_extension(file_path) == '.html'


def is_xml_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is an XML file."""
    return get_file_extension(file_path) == '.xml'


def count_files_in_directory(directory: Union[str, Path], pattern: str = "*") -> int:
    """Count files in a directory matching a pattern."""
    if isinstance(directory, str):
        directory = Path(directory)
    
    if not directory.exists() or not directory.is_dir():
        return 0
    
    return len(list(directory.glob(pattern)))


def get_file_info(file_path: Union[str, Path]) -> dict:
    """Get basic file information."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    try:
        stat = file_path.stat()
        return {
            'name': file_path.name,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': get_file_extension(file_path),
            'exists': file_path.exists(),
        }
    except Exception as e:
        logger.error(f"Failed to get file info for {file_path}: {e}")
        return {
            'name': str(file_path),
            'size': 0,
            'size_formatted': '0 B',
            'modified': None,
            'extension': '',
            'exists': False,
        }


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Validate and parse date range strings."""
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid start date format: {start_date}. Use YYYY-MM-DD format.")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid end date format: {end_date}. Use YYYY-MM-DD format.")
    
    if start_dt and end_dt and start_dt > end_dt:
        raise ValueError("Start date cannot be after end date.")
    
    return start_dt, end_dt


def is_date_in_range(date: datetime, start_date: Optional[datetime], end_date: Optional[datetime]) -> bool:
    """Check if a date falls within the specified range."""
    if start_date and date < start_date:
        return False
    if end_date and date > end_date:
        return False
    return True


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    html_escapes = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }
    
    for char, escape in html_escapes.items():
        text = text.replace(char, escape)
    
    return text


def unescape_html(text: str) -> str:
    """Unescape HTML entities."""
    html_unescapes = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'"
    }
    
    for escape, char in html_unescapes.items():
        text = text.replace(escape, char)
    
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    # Replace multiple whitespace characters with single space
    normalized = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    return normalized.strip()


def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text using regex."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return list(set(emails))  # Remove duplicates


def is_valid_email(email: str) -> bool:
    """Check if an email address is valid."""
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    return bool(re.match(email_pattern, email))


def get_memory_usage() -> dict:
    """Get current memory usage information."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms,  # Virtual Memory Size
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
        }
    except ImportError:
        return {
            'rss': 0,
            'vms': 0,
            'rss_mb': 0,
            'vms_mb': 0,
            'error': 'psutil not available'
        }


def log_memory_usage(logger_instance: logging.Logger, message: str = "Memory usage"):
    """Log current memory usage."""
    try:
        memory_info = get_memory_usage()
        logger_instance.info(
            f"{message}: RSS: {memory_info['rss_mb']:.1f} MB, "
            f"VMS: {memory_info['vms_mb']:.1f} MB"
        )
    except Exception as e:
        logger_instance.debug(f"Failed to log memory usage: {e}")


def create_backup_file(file_path: Union[str, Path]) -> Optional[Path]:
    """Create a backup of a file with timestamp suffix."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    if not file_path.exists():
        return None
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.{timestamp}{file_path.suffix}')
        
        # Copy the file
        import shutil
        shutil.copy2(file_path, backup_path)
        
        logger.info(f"Created backup: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return None


def cleanup_old_backups(directory: Union[str, Path], pattern: str = "*.backup", keep_count: int = 5):
    """Clean up old backup files, keeping only the most recent ones."""
    if isinstance(directory, str):
        directory = Path(directory)
    
    try:
        backup_files = list(directory.glob(pattern))
        if len(backup_files) <= keep_count:
            return
        
        # Sort by modification time (oldest first)
        backup_files.sort(key=lambda x: x.stat().st_mtime)
        
        # Remove oldest files
        files_to_remove = backup_files[:-keep_count]
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                logger.info(f"Removed old backup: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove backup {file_path}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to cleanup old backups in {directory}: {e}")
