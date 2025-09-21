"""
New Attachment Manager for Google Voice SMS Takeout XML Converter.

This module provides new implementations of attachment processing functions
that use PathManager for consistent, working directory independent path handling.
"""

import os
import shutil
import logging
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .path_manager import PathManager, PathValidationError, PathContext

logger = logging.getLogger(__name__)


def build_file_location_index_new(filenames: List[str], path_manager: PathManager) -> Dict[str, Path]:
    """
    New implementation of file location index using PathManager with caching optimization.
    
    Args:
        filenames: List of attachment filenames to index
        path_manager: PathManager instance for consistent path handling
        
    Returns:
        Dictionary mapping filename to full source Path
    """
    
    try:
        # PERFORMANCE OPTIMIZATION: Try to use cached index first
        cache_file = path_manager.processing_dir / ".attachment_cache.json"
        cached_index = _try_load_cached_index(cache_file, path_manager.processing_dir, filenames)
        
        if cached_index is not None:
            logger.info(f"✅ Using cached attachment index with {len(cached_index)} files")
            return cached_index
        
        # Cache miss or invalid - build fresh index
        filename_set = set(filenames)
        file_index = {}
        
        # Single directory tree walk to find all files
        logger.info("Scanning directory tree for file locations...")
        for root, dirs, files in os.walk(path_manager.processing_dir):
            for file in files:
                if file in filename_set:
                    source_file = Path(root) / file
                    if source_file.exists():
                        file_index[file] = source_file.resolve()
                        
                        if len(file_index) % 1000 == 0:
                            logger.info(f"Indexed {len(file_index)}/{len(filenames)} files...")
        
        logger.info(f"✅ File location index completed: {len(file_index)}/{len(filenames)} files found")
        
        # PERFORMANCE OPTIMIZATION: Save to cache for future runs
        _save_cached_index(cache_file, path_manager.processing_dir, file_index)
        
        return file_index
        
    except Exception as e:
        logger.error(f"❌ Error building file location index: {e}")
        raise


def _try_load_cached_index(cache_file: Path, processing_dir: Path, filenames: List[str]) -> Optional[Dict[str, Path]]:
    """
    Try to load cached attachment index if valid.
    
    Args:
        cache_file: Path to cache file
        processing_dir: Processing directory to validate against
        filenames: List of filenames being requested
        
    Returns:
        Cached index dict or None if cache is invalid/missing
    """
    try:
        if not cache_file.exists():
            return None
        
        # Load cache data
        cache_data = json.loads(cache_file.read_text())
        
        # Validate cache structure
        required_fields = ["scan_time", "file_count", "directory_hash", "index"]
        if not all(field in cache_data for field in required_fields):
            logger.debug("Cache invalid: missing required fields")
            return None
        
        # Validate directory hasn't changed (using hash of directory modification times)
        current_dir_hash = _compute_directory_hash(processing_dir)
        if cache_data["directory_hash"] != current_dir_hash:
            logger.debug("Cache invalid: directory structure changed")
            return None
        
        # Validate file count hasn't changed significantly
        if abs(cache_data["file_count"] - len(filenames)) > len(filenames) * 0.1:  # 10% tolerance
            logger.debug("Cache invalid: file count changed significantly")
            return None
        
        # Convert cached paths back to Path objects
        cached_index = {}
        for filename, path_str in cache_data["index"].items():
            if filename in filenames:  # Only return requested files
                cached_index[filename] = Path(path_str)
        
        logger.debug(f"Cache hit: loaded {len(cached_index)} files from cache")
        return cached_index
        
    except Exception as e:
        logger.debug(f"Cache load failed: {e}")
        return None


def _save_cached_index(cache_file: Path, processing_dir: Path, file_index: Dict[str, Path]) -> None:
    """
    Save attachment index to cache file.
    
    Args:
        cache_file: Path to cache file
        processing_dir: Processing directory
        file_index: File index to cache
    """
    try:
        cache_data = {
            "scan_time": time.time(),
            "file_count": len(file_index),
            "directory_hash": _compute_directory_hash(processing_dir),
            "index": {filename: str(path) for filename, path in file_index.items()}
        }
        
        # Write cache atomically
        temp_cache = cache_file.with_suffix('.tmp')
        temp_cache.write_text(json.dumps(cache_data, indent=2))
        temp_cache.replace(cache_file)
        
        logger.debug(f"Saved attachment index cache with {len(file_index)} files")
        
    except Exception as e:
        logger.debug(f"Failed to save cache: {e}")
        # Don't fail the whole operation if caching fails


def _compute_directory_hash(processing_dir: Path) -> str:
    """
    Compute a hash of the directory structure for cache validation.
    
    Args:
        processing_dir: Directory to hash
        
    Returns:
        Hash string representing directory state
    """
    try:
        # Use directory modification time and file count as a simple hash
        # This is much faster than hashing all file contents
        dir_stat = processing_dir.stat()
        calls_dir = processing_dir / "Calls"
        calls_stat = calls_dir.stat() if calls_dir.exists() else None
        
        hash_input = f"{dir_stat.st_mtime}_{dir_stat.st_size}"
        if calls_stat:
            hash_input += f"_{calls_stat.st_mtime}_{calls_stat.st_size}"
        
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]  # Short hash for performance
        
    except Exception:
        # If hashing fails, return random hash to force cache invalidation
        return "invalid"


def copy_mapped_attachments_new(
    src_filename_map: Dict[str, Tuple[str, Path]],
    path_manager: PathManager,
) -> None:
    """
    New implementation of attachment copying using PathManager.
    
    Args:
        src_filename_map: Mapping of src elements to (filename, source_path) tuples
        path_manager: PathManager instance for consistent path handling
    """
    
    # Filter out None entries at the start to avoid type validation errors
    valid_mappings = {
        src: (filename, source_path) 
        for src, (filename, source_path) in src_filename_map.items() 
        if source_path is not None
    }
    
    skipped_count = len(src_filename_map) - len(valid_mappings)
    if skipped_count > 0:
        logger.info(f"Skipping {skipped_count} entries with no attachment files (this is normal for text-only messages)")
    
    logger.info(f"Copying {len(valid_mappings)} valid attachments using PathManager")
    
    copied_count = 0
    failed_count = 0
    
    for src, (filename, source_path) in valid_mappings.items():
        try:
            # Validate source path (now guaranteed to be Path object)
            if not source_path.exists():
                logger.warning(f"Source file no longer exists: {source_path}")
                failed_count += 1
                continue
            
            # Get destination path from PathManager
            dest_path = path_manager.get_attachment_dest_path(filename)
            
            # Log path operation for debugging
            context = path_manager.get_path_context(
                "copy_attachment",
                source=source_path,
                destination=dest_path
            )
            path_manager.log_path_operation(context)
            
            # Safety check: prevent copying to same location
            if source_path.resolve() == dest_path.resolve():
                logger.info(f"Skipping {filename} - source and destination are the same")
                copied_count += 1
                continue
            
            # Copy file using absolute paths
            shutil.copy2(source_path, dest_path)
            copied_count += 1
            
            if copied_count % 100 == 0:
                logger.info(f"Copied {copied_count}/{len(valid_mappings)} attachments")
                
        except Exception as e:
            logger.error(f"Failed to copy {filename}: {e}")
            failed_count += 1
    
    logger.info(f"✅ Attachment copying completed. Successfully copied {copied_count}, failed {failed_count}")


def build_attachment_mapping_with_progress_new(
    path_manager: PathManager,
    sample_files: List[str] = None,
) -> Dict[str, Tuple[str, Path]]:
    """
    New implementation of attachment mapping using PathManager.
    
    Args:
        path_manager: PathManager instance for consistent path handling
        sample_files: Optional list of HTML files to limit processing to (for test mode)
        
    Returns:
        Dictionary mapping src elements to (filename, source_path) tuples
    """
    
    logger.info("Starting attachment mapping build process...")
    
    # Step 1: Extract src elements from HTML files
    if sample_files:
        logger.info(f"🧪 TEST MODE: Limiting src extraction to {len(sample_files)} sample files")
        src_to_files = extract_src_with_source_files_new(path_manager.processing_dir, sample_files=sample_files)
    else:
        src_to_files = extract_src_with_source_files_new(path_manager.processing_dir)
    
    src_elements = list(src_to_files.keys())
    
    # PERFORMANCE OPTIMIZATION: Early exit if no src elements found
    if not src_elements:
        logger.info("✅ No src elements found in HTML files - skipping attachment scanning for performance")
        logger.info("✅ Completed attachment mapping. Created 0 mappings from 0 src elements and 0 attachment files")
        return {}
    
    logger.info(f"Found {len(src_elements)} src elements, proceeding with attachment scanning...")
    
    # Step 2: Build file location index using PathManager
    att_filenames = list_att_filenames_with_progress_new(path_manager.processing_dir)
    file_location_index = build_file_location_index_new(att_filenames, path_manager)
    
    # Step 3: Create mapping with Path objects
    logger.info(
        f"Starting src-to-filename mapping for {len(src_elements)} src elements and {len(att_filenames)} attachment files"
    )
    
    # Create the src -> (filename, source_path) mapping
    mapping = {}
    used_attachments = set()
    
    for src in src_elements:
        if not src.strip():
            continue
        
        src_normalized = src.strip()
        
        # Check if this src directly matches an attachment filename
        if src_normalized in file_location_index:
            # Direct match - use this attachment
            assigned_filename = src_normalized
            source_path = file_location_index[src_normalized]
            
            if assigned_filename not in used_attachments:
                mapping[src_normalized] = (assigned_filename, source_path)
                used_attachments.add(assigned_filename)
                logger.debug(f"Direct match: {src_normalized} -> {assigned_filename}")
            else:
                logger.debug(f"Attachment {assigned_filename} already used, skipping {src_normalized}")
        else:
            # No direct match - try to find a suitable attachment
            # This handles cases where src might be a relative path or different naming
            assigned_filename = None
            source_path = None
            
            # First try the original indirect matching logic
            for attachment_filename in att_filenames:
                if attachment_filename not in used_attachments:
                    # Check if this attachment could be the one referenced by this src
                    # For now, use a simple heuristic: if the attachment filename contains
                    # the src (without extension), consider it a match
                    src_without_ext = src_normalized
                    if '.' in src_normalized:
                        src_without_ext = src_normalized.rsplit('.', 1)[0]
                    
                    if src_without_ext in attachment_filename or attachment_filename.startswith(src_without_ext):
                        assigned_filename = attachment_filename
                        source_path = file_location_index[attachment_filename]
                        break
            
            # If original logic failed, try enhanced Google Voice pattern matching
            if not assigned_filename:
                for attachment_filename in att_filenames:
                    if attachment_filename not in used_attachments:
                        # Pattern 1: Extract timestamp and type from src
                        src_parts = src_normalized.split(' - ')
                        if len(src_parts) >= 3:
                            timestamp_part = src_parts[2]  # e.g., "2024-10-20T14_50_55Z-6-1"
                            type_part = src_parts[1]      # e.g., "Text"
                            
                            logger.debug(f"Enhanced matching: src='{src_normalized}', timestamp_part='{timestamp_part}', type_part='{type_part}'")
                            logger.debug(f"Checking attachment: {attachment_filename}")
                            
                            # Look for attachments with similar timestamp and type
                            if (timestamp_part in attachment_filename and 
                                type_part.lower() in attachment_filename.lower()):
                                logger.debug(f"Timestamp/type match found: {src_normalized} -> {attachment_filename}")
                                assigned_filename = attachment_filename
                                source_path = file_location_index[attachment_filename]
                                break
                        
                        # Pattern 2: Try fuzzy matching on contact name
                        if not assigned_filename:
                            contact_name = src_parts[0] if src_parts else ""
                            if contact_name and len(contact_name) > 3:
                                logger.debug(f"Trying contact name matching: contact_name='{contact_name}'")
                                # Look for attachments containing the contact name
                                if contact_name.lower() in attachment_filename.lower():
                                    logger.debug(f"Contact name match found: {src_normalized} -> {attachment_filename}")
                                    assigned_filename = attachment_filename
                                    source_path = file_location_index[attachment_filename]
                                    break
            
            if assigned_filename:
                mapping[src_normalized] = (assigned_filename, source_path)
                used_attachments.add(assigned_filename)
                logger.debug(f"Indirect match: {src_normalized} -> {assigned_filename}")
            else:
                # Log as debug instead of warning for non-critical cases
                logger.debug(f"No attachment found for src: {src_normalized} (this may be normal for text-only messages)")
                # Still create a mapping to avoid processing errors
                mapping[src_normalized] = ("No attachment found", None)
    
    logger.info(
        f"✅ Completed attachment mapping. Created {len(mapping)} mappings from {len(src_elements)} src elements and {len(att_filenames)} attachment files"
    )
    
    return mapping


def extract_src_with_source_files_new(html_directory: Path, sample_files: List[str] = None) -> Dict[str, List[str]]:
    """
    New implementation of src extraction using Path objects.
    
    Args:
        html_directory: Directory to search for HTML files
        sample_files: Optional list of HTML files to limit processing to (for test mode)
        
    Returns:
        dict: Mapping from src/href values to list of HTML files that contain them
    """
    
    src_to_files = {}
    
    try:
        # Get total count of HTML files for progress tracking
        if sample_files:
            html_files = [Path(f) for f in sample_files if Path(f).exists()]
            total_files = len(html_files)
            logger.info(f"🧪 TEST MODE: Processing {total_files} sample HTML files")
        else:
            html_files = list(html_directory.rglob("*.html"))
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
                    buffering=32768,  # Use standard buffer size
                ) as file:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(file, "html.parser")
                    
                    # Extract image src attributes
                    img_srcs = [
                        img["src"]
                        for img in soup.select("img[src]")
                    ]
                    for src in img_srcs:
                        if src not in src_to_files:
                            src_to_files[src] = []
                        src_to_files[src].append(html_file.name)
                    
                    # Extract vCard href attributes
                    vcard_hrefs = [
                        a["href"]
                        for a in soup.select("a[href$='.vcf']")
                    ]
                    for src in vcard_hrefs:
                        if src not in src_to_files:
                            src_to_files[src] = []
                        src_to_files[src].append(html_file.name)
                
                # Report progress every 100 files
                if (i + 1) % 100 == 0:
                    logger.info(
                        f"Processed {i + 1}/{total_files} files, found {len(src_to_files)} unique src elements"
                    )
                
            except Exception as e:
                logger.warning(f"Failed to process {html_file}: {e}")
                continue
        
        logger.info(
            f"✅ Completed src extraction with source tracking from {total_files} files. Total unique src elements: {len(src_to_files)}"
        )
        
    except Exception as e:
        logger.error(
            f"❌ Failed to extract src with source tracking from {html_directory}: {e}"
        )
    
    return src_to_files


def list_att_filenames_with_progress_new(processing_directory: Path) -> List[str]:
    """
    New implementation of attachment filename listing using Path objects.
    
    Args:
        processing_directory: Directory to search for attachments
        
    Returns:
        List of attachment filenames
    """
    
    logger.info("Starting attachment filename collection...")
    
    try:
        # Define attachment file extensions
        attachment_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # Images
            '.vcf',  # vCards
            '.mp3', '.wav', '.m4a', '.aac',  # Audio
            '.mp4', '.mov', '.avi', '.mkv',  # Video
            '.pdf', '.doc', '.docx', '.txt'  # Documents
        }
        
        attachment_files = []
        
        # Walk through the processing directory
        for root, dirs, files in os.walk(processing_directory):
            logger.debug(f"Scanning directory: {root}")
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in attachment_extensions:
                    attachment_files.append(file)
                    logger.debug(f"Found attachment: {file} in {root}")
                
                # Progress reporting for large directories
                if len(attachment_files) % 1000 == 0:
                    logger.info(f"Found {len(attachment_files)} attachment files...")
        
        logger.info(f"✅ Attachment filename collection completed: {len(attachment_files)} files found")
        logger.debug(f"All attachment files found: {attachment_files}")
        return attachment_files
        
    except Exception as e:
        logger.error(f"❌ Error collecting attachment filenames: {e}")
        raise


def normalize_filename(filename: str) -> str:
    """
    Normalize filename for consistent comparison.
    
    Args:
        filename: Filename to normalize
        
    Returns:
        Normalized filename string
    """
    # Remove common file extensions for comparison
    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.vcf']
    
    normalized = filename
    for ext in extensions:
        if filename.lower().endswith(ext):
            normalized = filename[:-len(ext)]
            break
    
    return normalized
