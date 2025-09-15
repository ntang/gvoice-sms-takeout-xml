"""
Improved File Operations Module

This module provides enhanced file operations using the improved utilities
while maintaining the same interface as the existing functions.
"""

import logging
import threading
from pathlib import Path
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import improved utilities
from .improved_utils import copy_file_safely, ensure_directory_with_permissions, ProgressTracker

logger = logging.getLogger(__name__)

# Feature flags for gradual rollout
USE_IMPROVED_FILE_OPS = True  # Can be controlled via environment variable

# Global lock for file operations (maintained for compatibility)
FILE_OPERATIONS_LOCK = threading.Lock()


def copy_attachments_sequential_improved(filenames: Set[str], attachments_dir: Path) -> None:
    """
    Improved sequential attachment copying with better error handling and progress tracking.
    
    Args:
        filenames: Set of attachment filenames to copy
        attachments_dir: Destination directory for attachments
    """
    if not USE_IMPROVED_FILE_OPS:
        # Fallback to legacy implementation
        return _legacy_copy_attachments_sequential(filenames, attachments_dir)
    
    # Ensure destination directory exists with proper permissions
    if not ensure_directory_with_permissions(attachments_dir, 0o755):
        logger.error(f"Failed to create/access attachments directory: {attachments_dir}")
        return
    
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    # Use improved progress tracking
    with ProgressTracker("Copying attachments", len(filenames)) as progress:
        for filename in filenames:
            try:
                # Source file in Calls directory
                source_file = Path("Calls") / filename  # Relative to processing directory
                
                # Destination file in attachments directory
                dest_file = attachments_dir / filename
                
                if dest_file.exists():
                    logger.debug(f"Attachment already exists: {filename}")
                    skipped_count += 1
                    progress.update(1, f"Skipped: {filename}")
                    continue
                
                # Use improved file copying
                if copy_file_safely(source_file, dest_file, preserve_metadata=True):
                    copied_count += 1
                    progress.update(1, f"Copied: {filename}")
                else:
                    error_count += 1
                    progress.update(1, f"Failed: {filename}")
                    
            except Exception as e:
                logger.error(f"Failed to copy attachment {filename}: {e}")
                error_count += 1
                progress.update(1, f"Error: {filename}")
    
    logger.info(
        f"Attachment copying completed: {copied_count} copied, {skipped_count} skipped, {error_count} errors"
    )
    logger.info(f"Total attachments in directory: {len(list(attachments_dir.glob('*')))}")


def copy_attachments_parallel_improved(filenames: Set[str], attachments_dir: Path, max_workers: int = 4) -> None:
    """
    Improved parallel attachment copying with better error handling and progress tracking.
    
    Args:
        filenames: Set of attachment filenames to copy
        attachments_dir: Destination directory for attachments
        max_workers: Maximum number of worker threads
    """
    if not USE_IMPROVED_FILE_OPS:
        # Fallback to legacy implementation
        return _legacy_copy_attachments_parallel(filenames, attachments_dir, max_workers)
    
    # Ensure destination directory exists with proper permissions
    if not ensure_directory_with_permissions(attachments_dir, 0o755):
        logger.error(f"Failed to create/access attachments directory: {attachments_dir}")
        return
    
    # Convert set to list for indexing
    filename_list = list(filenames)
    
    # Split into chunks for parallel processing
    chunk_size = max(100, len(filename_list) // max_workers)
    chunks = [
        filename_list[i : i + chunk_size]
        for i in range(0, len(filename_list), chunk_size)
    ]
    
    # Thread-safe statistics tracking
    copied_count = 0
    skipped_count = 0
    error_count = 0
    stats_lock = threading.Lock()
    
    with ProgressTracker("Copying attachments in parallel", len(filenames)) as progress:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit chunk copying tasks
            future_to_chunk = {
                executor.submit(copy_chunk_parallel_improved, chunk, attachments_dir): chunk
                for chunk in chunks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                try:
                    chunk_result = future.result()
                    # Thread-safely aggregate statistics
                    with stats_lock:
                        copied_count += chunk_result["copied"]
                        skipped_count += chunk_result["skipped"]
                        error_count += chunk_result["errors"]
                    
                    # Update progress
                    progress.update(chunk_result["copied"] + chunk_result["skipped"] + chunk_result["errors"])
                    
                    # Log progress
                    logger.debug(
                        f"Chunk completed: {chunk_result['copied']} copied, {chunk_result['skipped']} skipped, {chunk_result['errors']} errors"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to process chunk: {e}")
                    continue
    
    logger.info(
        f"Parallel attachment copying completed: {copied_count} copied, {skipped_count} skipped, {error_count} errors"
    )
    
    # Thread-safe file operation for directory listing
    with FILE_OPERATIONS_LOCK:
        total_files = len(list(attachments_dir.glob("*")))
    
    logger.info(f"Total attachments in directory: {total_files}")


def copy_chunk_parallel_improved(filenames: List[str], attachments_dir: Path) -> Dict[str, int]:
    """
    Improved parallel chunk copying with better error handling.
    
    Args:
        filenames: List of filenames in this chunk
        attachments_dir: Destination directory for attachments
    
    Returns:
        Dict[str, int]: Copy statistics for this chunk
    """
    if not USE_IMPROVED_FILE_OPS:
        # Fallback to legacy implementation
        return _legacy_copy_chunk_parallel(filenames, attachments_dir)
    
    chunk_result = {"copied": 0, "skipped": 0, "errors": 0}
    
    for filename in filenames:
        try:
            # Source file in Calls directory
            source_file = Path("Calls") / filename  # Relative to processing directory
            
            # Destination file in attachments directory
            dest_file = attachments_dir / filename
            
            if dest_file.exists():
                chunk_result["skipped"] += 1
                continue
            
            # Use improved file copying
            if copy_file_safely(source_file, dest_file, preserve_metadata=True):
                chunk_result["copied"] += 1
            else:
                chunk_result["errors"] += 1
                
        except Exception as e:
            chunk_result["errors"] += 1
            logger.debug(f"Chunk exception: {e}")
            continue
    
    return chunk_result


# ====================================================================
# LEGACY IMPLEMENTATIONS FOR BACKWARD COMPATIBILITY
# ====================================================================

def _legacy_copy_attachments_sequential(filenames: Set[str], attachments_dir: Path) -> None:
    """Legacy sequential attachment copying implementation."""
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    for filename in filenames:
        try:
            # Source file in Calls directory
            source_file = Path("Calls") / filename
            
            if not source_file.exists():
                logger.error(f"Source attachment not found: {source_file}")
                error_count += 1
                continue
            
            # Destination file in attachments directory
            dest_file = attachments_dir / filename
            
            if dest_file.exists():
                logger.debug(f"Attachment already exists: {filename}")
                skipped_count += 1
                continue
            
            # Safety check: prevent copying to same location
            if source_file.resolve() == dest_file.resolve():
                logger.debug(f"Skipping {filename} - source and destination are the same")
                copied_count += 1
                continue
            
            # Try copy2 first, fallback to copy if cross-device error occurs
            import shutil
            try:
                shutil.copy2(source_file, dest_file)
            except OSError as copy_error:
                if "Invalid cross-device link" in str(copy_error) or "cross-device" in str(copy_error).lower():
                    logger.info(f"Cross-device link error for {filename}, using fallback copy method")
                    shutil.copy(source_file, dest_file)
                else:
                    raise copy_error
            
            copied_count += 1
            
            # Log progress every 100 files
            if copied_count % 100 == 0:
                logger.debug(f"Attachment copying progress: {copied_count}/{len(filenames)} copied")
                
        except Exception as e:
            logger.error(f"Failed to copy attachment {filename}: {e}")
            error_count += 1
    
    logger.info(
        f"Attachment copying completed: {copied_count} copied, {skipped_count} skipped, {error_count} errors"
    )
    logger.info(f"Total attachments in directory: {len(list(attachments_dir.glob('*')))}")


def _legacy_copy_attachments_parallel(filenames: Set[str], attachments_dir: Path, max_workers: int = 4) -> None:
    """Legacy parallel attachment copying implementation."""
    # Convert set to list for indexing
    filename_list = list(filenames)
    
    # Split into chunks for parallel processing
    chunk_size = max(100, len(filename_list) // max_workers)
    chunks = [
        filename_list[i : i + chunk_size]
        for i in range(0, len(filename_list), chunk_size)
    ]
    
    # Thread-safe statistics tracking
    copied_count = 0
    skipped_count = 0
    error_count = 0
    stats_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit chunk copying tasks
        future_to_chunk = {
            executor.submit(_legacy_copy_chunk_parallel, chunk, attachments_dir): chunk
            for chunk in chunks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            try:
                chunk_result = future.result()
                # Thread-safely aggregate statistics
                with stats_lock:
                    copied_count += chunk_result["copied"]
                    skipped_count += chunk_result["skipped"]
                    error_count += chunk_result["errors"]
                
                # Log progress
                logger.debug(
                    f"Chunk completed: {chunk_result['copied']} copied, {chunk_result['skipped']} skipped, {chunk_result['errors']} errors"
                )
                
            except Exception as e:
                logger.error(f"Failed to process chunk: {e}")
                continue
    
    logger.info(
        f"Parallel attachment copying completed: {copied_count} copied, {skipped_count} skipped, {error_count} errors"
    )
    
    # Thread-safe file operation for directory listing
    with FILE_OPERATIONS_LOCK:
        total_files = len(list(attachments_dir.glob("*")))
    
    logger.info(f"Total attachments in directory: {total_files}")


def _legacy_copy_chunk_parallel(filenames: List[str], attachments_dir: Path) -> Dict[str, int]:
    """Legacy parallel chunk copying implementation."""
    chunk_result = {"copied": 0, "skipped": 0, "errors": 0}
    
    for filename in filenames:
        try:
            # Source file in Calls directory
            source_file = Path("Calls") / filename
            
            if not source_file.exists():
                chunk_result["errors"] += 1
                continue
            
            # Destination file in attachments directory
            dest_file = attachments_dir / filename
            
            if dest_file.exists():
                chunk_result["skipped"] += 1
                continue
            
            # Safety check: prevent copying to same location
            if source_file.resolve() == dest_file.resolve():
                logger.debug(f"Skipping {filename} - source and destination are the same (chunk)")
                chunk_result["copied"] += 1
                continue
            
            # Try copy2 first, fallback to copy if cross-device error occurs
            import shutil
            try:
                shutil.copy2(source_file, dest_file)
            except OSError as copy_error:
                if "Invalid cross-device link" in str(copy_error) or "cross-device" in str(copy_error).lower():
                    logger.info(f"Cross-device link error for {filename}, using fallback copy method (chunk)")
                    shutil.copy(source_file, dest_file)
                else:
                    raise copy_error
            
            chunk_result["copied"] += 1
            
        except Exception as e:
            chunk_result["errors"] += 1
            logger.debug(f"Chunk exception: {e}")
            continue
    
    return chunk_result


# ====================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# ====================================================================

def copy_attachments_sequential(filenames: Set[str], attachments_dir: Path) -> None:
    """Backward compatibility wrapper for sequential attachment copying."""
    return copy_attachments_sequential_improved(filenames, attachments_dir)


def copy_attachments_parallel(filenames: Set[str], attachments_dir: Path, max_workers: int = 4) -> None:
    """Backward compatibility wrapper for parallel attachment copying."""
    return copy_attachments_parallel_improved(filenames, attachments_dir, max_workers)


def copy_chunk_parallel(filenames: List[str], attachments_dir: Path) -> Dict[str, int]:
    """Backward compatibility wrapper for parallel chunk copying."""
    return copy_chunk_parallel_improved(filenames, attachments_dir)
