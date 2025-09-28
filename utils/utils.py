"""
Utility functions for SMS/MMS processing.

This module contains common utility functions used throughout the SMS/MMS conversion process.
"""

import logging
import re
import os
import hashlib
import base64
from pathlib import Path
from typing import List, Optional, Union, Tuple
from datetime import datetime
import phonenumbers

logger = logging.getLogger(__name__)


def generate_unknown_number_hash(input_string: str) -> str:
    """
    Generate a consistent hash-based ID for unknown numbers.
    
    Args:
        input_string: String to hash (typically filename or conversation identifier)
        
    Returns:
        str: Hash-based ID with UN_ prefix and Base64 encoded MD5 hash
        
    Example:
        >>> generate_unknown_number_hash("John Doe - Text - 2024-01-01T12_00_00Z.html")
        'UN_XUFAKrxLKna5t2M'
    """
    # Generate MD5 hash (128 bits)
    hash_obj = hashlib.md5(input_string.encode('utf-8'))
    hash_bytes = hash_obj.digest()  # Get raw bytes
    
    # Encode in Base64 for maximum efficiency (22 characters)
    # Remove padding characters (=) and replace URL-unsafe chars
    hash_b64 = base64.urlsafe_b64encode(hash_bytes).decode('ascii')
    hash_b64 = hash_b64.rstrip('=')  # Remove padding
    
    return f"UN_{hash_b64}"


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
        r"tel:(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",  # tel:+1234567890
        r"(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",  # +1234567890
        r"(\+?\d{10,15})",  # Basic 10-15 digit numbers
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
    
    This function now uses the unified phone utilities module for consistent behavior.
    """
    from utils.phone_utils import is_valid_phone_number as validate_phone
    return validate_phone(phone_number, filter_non_phone)


def normalize_phone_number(phone_number: str) -> str:
    """Normalize a phone number to E.164 format."""
    from utils.phone_utils import normalize_phone_number as normalize_phone
    return normalize_phone(phone_number)


# Duplicate function removed


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(" .")
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"
    return sanitized


def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """Parse timestamp from filename using common patterns."""
    try:
        # Common timestamp patterns in filenames
        patterns = [
            r"(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}Z)",  # 2024-01-01T12_00_00Z
            r"(\d{4}-\d{2}-\d{2})",  # 2024-01-01
            r"(\d{8})",  # 20240101
            r"(\d{4}_\d{2}_\d{2})",  # 2024_01_01
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                timestamp_str = match.group(1)

                # Parse based on pattern
                if "T" in timestamp_str and "Z" in timestamp_str:
                    # Format: 2024-01-01T12_00_00Z
                    timestamp_str = timestamp_str.replace("_", ":")
                    return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
                elif "-" in timestamp_str:
                    # Format: 2024-01-01
                    return datetime.strptime(timestamp_str, "%Y-%m-%d")
                elif "_" in timestamp_str:
                    # Format: 2024_01_01
                    return datetime.strptime(timestamp_str, "%Y_%m_%d")
                else:
                    # Format: 20240101
                    return datetime.strptime(timestamp_str, "%Y%m%d")

        return None

    except Exception as e:
        logger.debug(f"Failed to parse timestamp from filename '{filename}': {e}")
        return None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes is None or size_bytes < 0:
        return "Unknown"
    
    try:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    except (TypeError, ZeroDivisionError) as e:
        logger.warning(f"Division error in file size formatting: {e}")
        return "Unknown"


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
    return get_file_extension(file_path) == ".html"


def is_xml_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is an XML file."""
    return get_file_extension(file_path) == ".xml"


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
            "name": file_path.name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "extension": get_file_extension(file_path),
            "exists": file_path.exists(),
        }
    except Exception as e:
        logger.error(f"Failed to get file info for {file_path}: {e}")
        return {
            "name": str(file_path),
            "size": 0,
            "size_formatted": "0 B",
            "modified": None,
            "extension": "",
            "exists": False,
        }


def validate_date_range(
    start_date: Optional[str], end_date: Optional[str]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Validate and parse date range strings."""
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid start date format: {start_date}. Use YYYY-MM-DD format."
            )

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid end date format: {end_date}. Use YYYY-MM-DD format."
            )

    if start_dt and end_dt and start_dt > end_dt:
        raise ValueError("Start date cannot be after end date.")

    return start_dt, end_dt


def is_date_in_range(
    date: datetime, start_date: Optional[datetime], end_date: Optional[datetime]
) -> bool:
    """Check if a date falls within the specified range."""
    if start_date and date < start_date:
        return False
    if end_date and date > end_date:
        return False
    return True


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    html_escapes = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}

    for char, escape in html_escapes.items():
        text = text.replace(char, escape)

    return text


def unescape_html(text: str) -> str:
    """Unescape HTML entities."""
    html_unescapes = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
    }

    for escape, char in html_unescapes.items():
        text = text.replace(escape, char)

    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    # Replace multiple whitespace characters with single space
    normalized = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    return normalized.strip()


def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text using regex."""
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    emails = re.findall(email_pattern, text)
    return list(set(emails))  # Remove duplicates


def is_valid_email(email: str) -> bool:
    """Check if an email address is valid."""
    email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$"
    return bool(re.match(email_pattern, email))


# ====================================================================
# ATTACHMENT COPYING FUNCTIONS (Consolidated from improved_file_operations.py)
# ====================================================================

def copy_attachments_sequential(filenames: set, attachments_dir: Path) -> None:
    """
    Copy attachments sequentially with error handling and progress tracking.
    
    Args:
        filenames: Set of attachment filenames to copy
        attachments_dir: Destination directory for attachments
    """
    import shutil
    
    # Ensure destination directory exists
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    logger.info(f"Starting sequential copy of {len(filenames)} attachments")
    
    for filename in filenames:
        try:
            # Source file in Calls directory
            source_file = Path("Calls") / filename  # Relative to processing directory
            
            # Destination file in attachments directory
            dest_file = attachments_dir / filename
            
            if dest_file.exists():
                logger.debug(f"Attachment already exists: {filename}")
                skipped_count += 1
                continue
            
            # Copy file with metadata preservation
            shutil.copy2(source_file, dest_file)
            copied_count += 1
            logger.debug(f"Copied: {filename}")
                    
        except Exception as e:
            logger.error(f"Failed to copy attachment {filename}: {e}")
            error_count += 1
    
    logger.info(
        f"Attachment copying completed: {copied_count} copied, {skipped_count} skipped, {error_count} errors"
    )


def copy_attachments_parallel(filenames: set, attachments_dir: Path, max_workers: int = 4) -> None:
    """
    Copy attachments in parallel with error handling and progress tracking.
    
    Args:
        filenames: Set of attachment filenames to copy
        attachments_dir: Destination directory for attachments
        max_workers: Maximum number of worker threads
    """
    import shutil
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Ensure destination directory exists
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    def copy_single_file(filename):
        """Copy a single file and return result."""
        try:
            source_file = Path("Calls") / filename
            dest_file = attachments_dir / filename
            
            if dest_file.exists():
                return {"filename": filename, "status": "skipped", "error": None}
            
            shutil.copy2(source_file, dest_file)
            return {"filename": filename, "status": "copied", "error": None}
            
        except Exception as e:
            return {"filename": filename, "status": "error", "error": str(e)}
    
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    logger.info(f"Starting parallel copy of {len(filenames)} attachments with {max_workers} workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all copy tasks
        future_to_filename = {executor.submit(copy_single_file, filename): filename 
                             for filename in filenames}
        
        # Process completed tasks
        for future in as_completed(future_to_filename):
            result = future.result()
            
            if result["status"] == "copied":
                copied_count += 1
                logger.debug(f"Copied: {result['filename']}")
            elif result["status"] == "skipped":
                skipped_count += 1
                logger.debug(f"Skipped: {result['filename']}")
            else:  # error
                error_count += 1
                logger.error(f"Failed to copy {result['filename']}: {result['error']}")
    
    logger.info(
        f"Parallel attachment copying completed: {copied_count} copied, {skipped_count} skipped, {error_count} errors"
    )


def copy_chunk_parallel(filenames: list, attachments_dir: Path) -> dict:
    """
    Copy a chunk of attachments in parallel and return statistics.
    
    Args:
        filenames: List of attachment filenames to copy
        attachments_dir: Destination directory for attachments
        
    Returns:
        dict: Statistics about the copy operation
    """
    import shutil
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Ensure destination directory exists
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    def copy_single_file(filename):
        """Copy a single file and return result."""
        try:
            source_file = Path("Calls") / filename
            dest_file = attachments_dir / filename
            
            if dest_file.exists():
                return {"filename": filename, "status": "skipped", "error": None}
            
            shutil.copy2(source_file, dest_file)
            return {"filename": filename, "status": "copied", "error": None}
            
        except Exception as e:
            return {"filename": filename, "status": "error", "error": str(e)}
    
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all copy tasks
        future_to_filename = {executor.submit(copy_single_file, filename): filename 
                             for filename in filenames}
        
        # Process completed tasks
        for future in as_completed(future_to_filename):
            result = future.result()
            
            if result["status"] == "copied":
                copied_count += 1
            elif result["status"] == "skipped":
                skipped_count += 1
            else:  # error
                error_count += 1
                logger.error(f"Failed to copy {result['filename']}: {result['error']}")
    
    return {
        "copied": copied_count,
        "skipped": skipped_count,
        "errors": error_count,
        "total": len(filenames)
    }


def get_memory_usage() -> dict:
    """Get current memory usage information."""
    try:
        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            "rss": memory_info.rss,  # Resident Set Size
            "vms": memory_info.vms,  # Virtual Memory Size
            "rss_mb": memory_info.rss / 1024 / 1024 if memory_info.rss is not None else 0,
            "vms_mb": memory_info.vms / 1024 / 1024 if memory_info.vms is not None else 0,
        }
    except ImportError:
        return {
            "rss": 0,
            "vms": 0,
            "rss_mb": 0,
            "vms_mb": 0,
            "error": "psutil not available",
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}{file_path.suffix}")

        # Copy the file
        import shutil
        
        # Safety check: prevent copying to same location
        if file_path.resolve() == backup_path.resolve():
            logger.warning(f"Skipping backup - source and destination are the same: {file_path}")
            return None
        
        # Try copy2 first, fallback to copy if cross-device error occurs
        try:
            shutil.copy2(file_path, backup_path)
        except OSError as copy_error:
            if "Invalid cross-device link" in str(copy_error) or "cross-device" in str(copy_error).lower():
                logger.info(f"Cross-device link error for backup, using fallback copy method")
                shutil.copy(file_path, backup_path)
            else:
                raise copy_error

        logger.info(f"Created backup: {backup_path}")
        return backup_path

    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return None


def cleanup_old_backups(
    directory: Union[str, Path], pattern: str = "*.backup", keep_count: int = 5
):
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
