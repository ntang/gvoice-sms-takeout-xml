"""
Attachment Manager Module for SMS/MMS conversion.

This module handles the mapping, copying, and management of attachments
(images, vCards, etc.) for Google Voice takeout files.
"""

import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from processors.html_processor import STRING_POOL

logger = logging.getLogger(__name__)


def extract_src_with_source_files(html_directory: str = None, sample_files: List[str] = None) -> Dict[str, List[str]]:
    """
    Extract image src attributes and vCard href attributes from HTML files with their source file information.

    Args:
        html_directory: Directory to search for HTML files (defaults to current directory)
        sample_files: Optional list of HTML files to limit processing to (for test mode)

    Returns:
        dict: Mapping from src/href values to list of HTML files that contain them
    """
    if html_directory is None:
        html_directory = "."

    src_to_files = {}

    try:
        # Get total count of HTML files for progress tracking
        if sample_files:
            html_files = [Path(f) for f in sample_files if Path(f).exists()]
            total_files = len(html_files)
            logger.info(f"🧪 TEST MODE: Processing {total_files} sample HTML files")
        else:
            html_files = list(Path(html_directory).rglob("*.html"))
            total_files = len(html_files)

        if html_files == 0:
            logger.error(f"No HTML files found in {html_directory}")
            return src_to_files

        logger.info(
            f"Starting src extraction with source tracking from {total_files} HTML files"
        )

        for i, html_file in enumerate(html_files):
            try:
                with open(
                    html_file,
                    "r",
                    encoding="utf-8",
                    buffering=STRING_POOL.FILE_READ_BUFFER_SIZE,
                ) as file:
                    soup = BeautifulSoup(file, STRING_POOL.HTML_PARSER)

                    # Extract image src attributes - use cached selector for performance
                    img_srcs = [
                        img["src"]
                        for img in soup.select(
                            STRING_POOL.ADDITIONAL_SELECTORS["img_src"]
                        )
                    ]
                    for src in img_srcs:
                        if src not in src_to_files:
                            src_to_files[src] = []
                        src_to_files[src].append(str(html_file.name))

                    # Extract vCard href attributes - use cached selector for performance
                    vcard_hrefs = [
                        a["href"]
                        for a in soup.select(
                            STRING_POOL.ADDITIONAL_SELECTORS["vcard_links"]
                        )
                    ]
                    for src in vcard_hrefs:
                        if src not in src_to_files:
                            src_to_files[src] = []
                        src_to_files[src].append(str(html_file.name))

                # Report progress every 100 files
                if (i + 1) % 100 == 0:
                    logger.info(
                        f"Processed {i + 1}/{total_files} files, found {len(src_to_files)} unique src elements"
                    )

            except Exception as e:
                logger.warning(f"Failed to process {html_file}: {e}")
                continue

        logger.info(
            f"Completed src extraction with source tracking from {total_files} files. Total unique src elements: {len(src_to_files)}"
        )

    except Exception as e:
        logger.error(
            f"Failed to extract src with source tracking from {html_directory}: {e}"
        )

    return src_to_files


def list_att_filenames_with_progress(processing_directory: str = None) -> List[str]:
    """
    List all attachment filenames in the processing directory with progress tracking.

    Args:
        processing_directory: Directory to search for attachments

    Returns:
        List of attachment filenames
    """
    if processing_directory is None:
        processing_directory = "."

    att_filenames = []

    try:
        # Look for common attachment file extensions
        attachment_extensions = [
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.gif",
            "*.bmp",
            "*.webp",  # Images
            "*.vcf",
            "*.vcard",  # vCards
            "*.mp3",
            "*.wav",
            "*.m4a",  # Audio files
            "*.mp4",
            "*.avi",
            "*.mov",  # Video files
        ]

        total_files = 0
        for ext in attachment_extensions:
            files = list(Path(processing_directory).rglob(ext))
            total_files += len(files)

        logger.info(f"Found {total_files} potential attachment files")

        # Collect all attachment files
        for ext in attachment_extensions:
            files = list(Path(processing_directory).rglob(ext))
            for file_path in files:
                att_filenames.append(file_path.name)

        logger.info(f"Collected {len(att_filenames)} attachment filenames")

    except Exception as e:
        logger.error(f"Failed to list attachment filenames: {e}")

    return att_filenames


def normalize_filename(filename: str) -> str:
    """
    Normalize a filename for consistent comparison.

    Args:
        filename: Original filename

    Returns:
        Normalized filename
    """
    # Remove common file extensions
    base_name = filename
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".vcf", ".vcard"]:
        if filename.lower().endswith(ext):
            base_name = filename[: -len(ext)]
            break

    # Remove common prefixes/suffixes
    base_name = base_name.replace("att_", "").replace("_att", "")

    return base_name


def build_file_location_index(filenames: List[str], processing_directory: str) -> Dict[str, str]:
    """
    Build a file location index for all attachment files.
    This is the key optimization - we scan the directory tree ONCE.
    
    Args:
        filenames: List of attachment filenames to index
        processing_directory: Directory to search in
        
    Returns:
        Dictionary mapping filename to full source path
    """
    logger.info(f"Building file location index for {len(filenames)} files...")
    file_index = {}
    
    try:
        # Convert filenames to set for O(1) lookup
        filename_set = set(filenames)
        
        # Single directory tree walk to find all files
        logger.info("Scanning directory tree for file locations...")
        for root, dirs, files in os.walk(processing_directory):
            # Find all matching files in this directory
            for file in files:
                if file in filename_set:
                    source_file = Path(root) / file
                    if source_file.exists():
                        file_index[file] = str(source_file)
                        
                        # Log progress every 1000 files
                        if len(file_index) % 1000 == 0:
                            logger.info(f"Indexed {len(file_index)}/{len(filenames)} files...")
        
        logger.info(f"File location index completed: {len(file_index)}/{len(filenames)} files found")
        return file_index
        
    except Exception as e:
        logger.error(f"Error building file location index: {e}")
        return {}


def find_attachment_source_path(filename: str, processing_directory: str) -> str:
    """
    Find the source file path for a given attachment filename.
    
    Args:
        filename: The attachment filename to find
        processing_directory: Directory to search in
        
    Returns:
        Full path to the source file, or None if not found
    """
    try:
        # Look for the attachment file in the processing directory and subdirectories
        for root, dirs, files in os.walk(processing_directory):
            if filename in files:
                source_file = Path(root) / filename
                if source_file.exists():
                    return str(source_file)
        return None
    except Exception as e:
        logger.warning(f"Error finding source path for {filename}: {e}")
        return None


def build_attachment_mapping_with_progress(
    processing_directory: str = None,
    sample_files: List[str] = None,
) -> Dict[str, Tuple[str, str]]:
    """
    Build mapping from src elements to attachment filenames with progress tracking.

    Args:
        processing_directory: Directory to search for HTML files and attachments
        sample_files: Optional list of HTML files to limit processing to (for test mode)

    Returns:
        Dictionary mapping src elements to (filename, source_path) tuples
    """
    if processing_directory is None:
        processing_directory = "."

    logger.info("Starting attachment mapping build process...")

    # Step 1: Extract src elements from HTML files with source tracking
    logger.info("Starting src extraction from HTML files with source tracking")
    if sample_files:
        logger.info(f"🧪 TEST MODE: Limiting src extraction to {len(sample_files)} sample files")
        src_to_files = extract_src_with_source_files(processing_directory, sample_files=sample_files)
    else:
        src_to_files = extract_src_with_source_files(processing_directory)
    src_elements = list(src_to_files.keys())

    # Step 2: Scan for attachment files and build file location index ONCE
    logger.info("Starting attachment scan and file location indexing...")
    att_filenames = list_att_filenames_with_progress(processing_directory)
    
    # Build file location index once - this is the key optimization
    logger.info("Building file location index...")
    file_location_index = build_file_location_index(att_filenames, processing_directory)
    logger.info(f"File location index built with {len(file_location_index)} entries")

    # Step 3: Create mapping
    logger.info(
        f"Starting src-to-filename mapping for {len(src_elements)} src elements and {len(att_filenames)} attachment files"
    )

    # Pre-normalize filenames to avoid repeated processing
    normalized_attachments = {}
    for filename in att_filenames:
        normalized = normalize_filename(filename)
        if normalized not in normalized_attachments:
            normalized_attachments[normalized] = filename

    # Create comprehensive mapping that finds ALL attachments for each HTML file
    mapping = {}

    # First, create a reverse mapping: HTML base filename -> list of all matching attachments
    html_to_attachments = {}

    # Pre-process HTML files to avoid repeated string operations
    html_bases = set()
    for html_list in src_to_files.values():
        for html_file in html_list:
            html_base = html_file.replace(".html", "")
            html_bases.add(html_base)

    # Sort attachment filenames for binary search optimization
    att_filenames_sorted = sorted(att_filenames)

    # Create mapping using more efficient algorithm
    for html_base in html_bases:
        # Use binary search approach for finding matching attachments
        matching_attachments = []

        # Find the first attachment that starts with this HTML base
        start_idx = 0
        while start_idx < len(att_filenames_sorted):
            filename = att_filenames_sorted[start_idx]
            if filename.startswith(html_base):
                # Found a match, collect all consecutive matches
                while start_idx < len(att_filenames_sorted) and att_filenames_sorted[
                    start_idx
                ].startswith(html_base):
                    matching_attachments.append(att_filenames_sorted[start_idx])
                    start_idx += 1
                break
            elif filename < html_base:
                start_idx += 1
            else:
                break

        if matching_attachments:
            html_to_attachments[html_base] = matching_attachments
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"HTML '{html_base}' has {len(matching_attachments)} attachments: {matching_attachments[:3]}{'...' if len(matching_attachments) > 3 else ''}"
                )

    # Now create the src -> (filename, source_path) mapping using more efficient algorithms
    # Pre-compute used attachments set for O(1) lookups
    used_attachments = set()

    # Use list comprehension for faster mapping creation
    mapping_items = []

    for src in src_elements:
        if not src.strip():
            continue

        src_normalized = src.strip()
        assigned_filename = None
        source_path = None

        if src_normalized in src_to_files:
            # Get the HTML files that contain this src reference
            html_files = src_to_files[src_normalized]

            # Find the first HTML file that has matching attachments
            for html_file in html_files:
                html_base = html_file.replace(".html", "")

                if html_base in html_to_attachments:
                    # Get the first available attachment for this HTML file
                    available_attachments = html_to_attachments[html_base]

                    # Find the first unused attachment
                    for attachment in available_attachments:
                        if attachment not in used_attachments:
                            assigned_filename = attachment
                            used_attachments.add(attachment)
                            break

                    if assigned_filename:
                        break

        if assigned_filename:
            # Use the pre-built file location index instead of searching
            source_path = file_location_index.get(assigned_filename)
            if source_path:
                mapping[src_normalized] = (assigned_filename, source_path)
                mapping_items.append((src_normalized, (assigned_filename, source_path)))
            else:
                logger.warning(f"Could not find source path for attachment: {assigned_filename}")

    logger.info(
        f"Completed attachment mapping. Created {len(mapping)} mappings from {len(src_elements)} src elements and {len(att_filenames)} attachment files"
    )

    return mapping


def copy_mapped_attachments(
    src_filename_map: Dict[str, Tuple[str, str]],
    output_directory: str = None,
    source_directory: str = None,
) -> None:
    """
    Copy all mapped attachments to the output directory.

    Args:
        src_filename_map: Mapping of src elements to (filename, source_path) tuples
        output_directory: Directory to copy attachments to
        source_directory: Directory containing the source attachment files (fallback)
    """
    if output_directory is None:
        output_directory = "conversations"

    if source_directory is None:
        # Default to current directory if not specified
        source_directory = "."

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Copying {len(src_filename_map)} mapped attachments from {source_directory} to {output_path}"
    )

    copied_count = 0
    failed_count = 0

    for src, (filename, source_path) in src_filename_map.items():
        try:
            # Use the pre-computed source path for direct access
            if source_path:
                source_file = Path(source_path)
                if source_file.exists():
                    dest_file = output_path / filename
                    
                    # Safety check: prevent copying to same location
                    if source_file.resolve() == dest_file.resolve():
                        logger.info(f"Skipping {filename} - source and destination are the same")
                        copied_count += 1
                        continue
                    
                    # Try copy2 first, fallback to copy if cross-device error occurs
                    try:
                        shutil.copy2(source_file, dest_file)
                    except OSError as copy_error:
                        if "Invalid cross-device link" in str(copy_error) or "cross-device" in str(copy_error).lower():
                            logger.info(f"Cross-device link error for {filename}, using fallback copy method")
                            shutil.copy(source_file, dest_file)
                        else:
                            raise copy_error
                    
                    copied_count += 1

                    if copied_count % 100 == 0:
                        logger.info(
                            f"Copied {copied_count}/{len(src_filename_map)} attachments"
                        )
                else:
                    logger.warning(f"Source file no longer exists: {source_path}")
                    failed_count += 1
            else:
                # Fallback: search for the file if source path is not available
                logger.warning(f"No source path available for {filename}, falling back to search")
                source_file = None
                for root, dirs, files in os.walk(source_directory):
                    if filename in files:
                        source_file = Path(root) / filename
                        break

                if source_file and source_file.exists():
                    dest_file = output_path / filename
                    
                    # Safety check: prevent copying to same location
                    if source_file.resolve() == dest_file.resolve():
                        logger.info(f"Skipping {filename} - source and destination are the same (fallback)")
                        copied_count += 1
                        continue
                    
                    # Try copy2 first, fallback to copy if cross-device error occurs
                    try:
                        shutil.copy2(source_file, dest_file)
                    except OSError as copy_error:
                        if "Invalid cross-device link" in str(copy_error) or "cross-device" in str(copy_error).lower():
                            logger.info(f"Cross-device link error for {filename}, using fallback copy method (fallback)")
                            shutil.copy(source_file, dest_file)
                        else:
                            raise copy_error
                    
                    copied_count += 1

                    if copied_count % 100 == 0:
                        logger.info(
                            f"Copied {copied_count}/{len(src_filename_map)} attachments (fallback)"
                        )
                else:
                    logger.warning(f"Attachment file not found: {filename}")
                    failed_count += 1

        except Exception as e:
            logger.error(f"Failed to copy attachment {filename}: {e}")
            failed_count += 1

    logger.info(
        f"Attachment copying completed. Successfully copied {copied_count}, failed {failed_count}"
    )


def copy_attachments_parallel(
    filenames: Set[str], attachments_dir: Path, max_workers: int = 4
) -> None:
    """
    Copy attachments in parallel for better performance.

    Args:
        filenames: Set of attachment filenames to copy
        attachments_dir: Directory containing the attachments
        max_workers: Maximum number of parallel workers
    """
    logger.info(
        f"Copying {len(filenames)} attachments in parallel using {max_workers} workers"
    )

    def copy_single_attachment(filename: str) -> bool:
        try:
            source_file = attachments_dir / filename
            if source_file.exists():
                # Copy to conversations directory
                dest_file = Path("conversations") / filename
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Safety check: prevent copying to same location
                if source_file.resolve() == dest_file.resolve():
                    logger.info(f"Skipping {filename} - source and destination are the same (parallel)")
                    return True
                
                # Try copy2 first, fallback to copy if cross-device error occurs
                try:
                    shutil.copy2(source_file, dest_file)
                except OSError as copy_error:
                    if "Invalid cross-device link" in str(copy_error) or "cross-device" in str(copy_error).lower():
                        logger.info(f"Cross-device link error for {filename}, using fallback copy method (parallel)")
                        shutil.copy(source_file, dest_file)
                    else:
                        raise copy_error
                
                return True
            else:
                logger.warning(f"Attachment file not found: {filename}")
                return False
        except Exception as e:
            logger.error(f"Failed to copy attachment {filename}: {e}")
            return False

    # Thread-safe statistics tracking
    completed = 0
    failed = 0
    stats_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all copy tasks
        future_to_filename = {
            executor.submit(copy_single_attachment, filename): filename
            for filename in filenames
        }

        # Process completed tasks
        for future in as_completed(future_to_filename):
            filename = future_to_filename[future]
            try:
                result = future.result()
                # Thread-safely update statistics
                with stats_lock:
                    if result:
                        completed += 1
                    else:
                        failed += 1

                    # Log progress every 100 attachments
                    if (completed + failed) % 100 == 0:
                        logger.info(
                            f"Progress: {completed + failed}/{len(filenames)} attachments processed"
                        )

            except Exception as e:
                logger.error(f"Exception occurred while copying {filename}: {e}")
                with stats_lock:
                    failed += 1

    logger.info(
        f"Parallel attachment copying completed. Successfully copied {completed}, failed {failed}"
    )


def validate_attachment_mapping(src_filename_map: Dict[str, str]) -> Dict[str, int]:
    """
    Validate the attachment mapping for completeness and correctness.

    Args:
        src_filename_map: Mapping of src elements to attachment filenames

    Returns:
        Dictionary with validation statistics
    """
    validation_stats = {
        "total_mappings": len(src_filename_map),
        "valid_mappings": 0,
        "invalid_mappings": 0,
        "missing_attachments": 0,
        "duplicate_attachments": 0,
    }

    # Check for duplicate attachments
    attachment_counts = {}
    for src, filename in src_filename_map.items():
        if filename in attachment_counts:
            attachment_counts[filename] += 1
            validation_stats["duplicate_attachments"] += 1
        else:
            attachment_counts[filename] = 1

    # Check if attachments exist
    for src, filename in src_filename_map.items():
        attachment_found = False
        for root, dirs, files in os.walk("."):
            if filename in files:
                attachment_found = True
                break

        if attachment_found:
            validation_stats["valid_mappings"] += 1
        else:
            validation_stats["missing_attachments"] += 1
            validation_stats["invalid_mappings"] += 1

    return validation_stats
