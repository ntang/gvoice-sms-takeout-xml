"""
Attachment Mapping Stage

Maps HTML src attributes to attachment filenames and generates a JSON file
for use by subsequent pipeline stages.

This stage implements smart caching (Option A):
- Tracks directory hash to detect file changes
- Validates output file exists before skipping
- Integrates with both attachment cache and pipeline state
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Tuple

from ..base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


def compute_directory_hash(processing_dir: Path) -> str:
    """
    Compute a hash of the directory structure for validation.

    Uses directory modification time, size, and file count to detect changes.
    This is faster than hashing all file contents.

    Args:
        processing_dir: Directory to hash

    Returns:
        Hash string representing directory state
    """
    try:
        # Use directory stats for quick validation
        dir_stat = processing_dir.stat()
        calls_dir = processing_dir / "Calls"
        calls_stat = calls_dir.stat() if calls_dir.exists() else None

        # Count HTML files (faster than counting all files)
        file_count = sum(1 for _ in processing_dir.glob("**/*.html"))

        hash_input = f"{dir_stat.st_mtime}_{dir_stat.st_size}_{file_count}"
        if calls_stat:
            hash_input += f"_{calls_stat.st_mtime}_{calls_stat.st_size}"

        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    except Exception as e:
        logger.debug(f"Failed to compute directory hash: {e}")
        # Return unique hash to force rebuild on error
        return f"error_{time.time()}"


def count_files_in_directory(processing_dir: Path) -> int:
    """
    Count HTML files in processing directory.

    Args:
        processing_dir: Directory to count files in

    Returns:
        Number of HTML files found
    """
    try:
        return sum(1 for _ in processing_dir.glob("**/*.html"))
    except Exception:
        return 0


class AttachmentMappingStage(PipelineStage):
    """
    Maps HTML src attributes to attachment filenames.

    This stage wraps the existing build_attachment_mapping_optimized()
    function and saves the result as JSON for pipeline consumption.

    Features:
    - Smart caching with validation
    - Directory change detection
    - Idempotent execution
    """

    def __init__(self):
        super().__init__("attachment_mapping")

    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute attachment mapping stage.

        Args:
            context: Pipeline context

        Returns:
            StageResult: Mapping results with validation metadata
        """
        start_time = time.time()

        try:
            logger.info("🔍 Starting attachment mapping...")

            # Use existing optimized function
            from core.performance_optimizations import build_attachment_mapping_optimized

            # Compute directory hash for validation
            directory_hash = compute_directory_hash(context.processing_dir)
            file_count = count_files_in_directory(context.processing_dir)

            logger.info(f"   Directory hash: {directory_hash}")
            logger.info(f"   HTML files: {file_count}")

            # Build the mapping
            src_filename_map = build_attachment_mapping_optimized(
                processing_dir=context.processing_dir,
                sample_files=None,  # Process all files
                use_cache=True
            )

            # Save to JSON for pipeline consumption
            output_file = context.output_dir / "attachment_mapping.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to serializable format
            mapping_data = {
                "metadata": {
                    "created_at": time.time(),
                    "total_mappings": len(src_filename_map),
                    "processing_dir": str(context.processing_dir),
                    "directory_hash": directory_hash,
                    "file_count": file_count
                },
                "mappings": {
                    src: {
                        "filename": filename,
                        "source_path": str(source_path)
                    }
                    for src, (filename, source_path) in src_filename_map.items()
                }
            }

            with open(output_file, 'w') as f:
                json.dump(mapping_data, f, indent=2)

            execution_time = time.time() - start_time

            logger.info(f"✅ Attachment mapping completed in {execution_time:.2f}s")
            logger.info(f"   📊 Total mappings: {len(src_filename_map)}")
            logger.info(f"   💾 Saved to: {output_file}")

            return StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=len(src_filename_map),
                output_files=[output_file],
                metadata={
                    "total_mappings": len(src_filename_map),
                    "output_file": str(output_file),
                    "directory_hash": directory_hash,
                    "file_count": file_count
                }
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Attachment mapping failed: {e}", exc_info=True)

            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"Attachment mapping failed: {str(e)}"]
            )

    def can_skip(self, context: PipelineContext) -> bool:
        """
        Smart validation for skipping (Option A implementation).

        Checks:
        1. Did stage complete successfully? (pipeline state)
        2. Does output file still exist?
        3. Has directory changed since last run? (hash comparison)
        4. Has file count changed significantly? (>10%)

        Args:
            context: Pipeline context

        Returns:
            bool: True if safe to skip, False if must rerun
        """
        # Check if stage ever completed
        if not context.has_stage_completed(self.name):
            logger.debug(f"Cannot skip {self.name}: never completed")
            return False

        # Check if output file exists
        output_file = context.output_dir / "attachment_mapping.json"
        if not output_file.exists():
            logger.debug(f"Cannot skip {self.name}: output file missing")
            return False

        # Get validation data from previous run
        stage_data = context.get_stage_data(self.name)
        if not stage_data:
            logger.debug(f"Cannot skip {self.name}: no stage data")
            return False

        previous_hash = stage_data.get('directory_hash')
        previous_count = stage_data.get('file_count', 0)

        if not previous_hash:
            logger.debug(f"Cannot skip {self.name}: no previous hash")
            return False

        # Compute current hash
        current_hash = compute_directory_hash(context.processing_dir)
        current_count = count_files_in_directory(context.processing_dir)

        # Check if directory changed
        if current_hash != previous_hash:
            logger.info(f"Cannot skip {self.name}: directory hash changed")
            logger.info(f"   Previous: {previous_hash}")
            logger.info(f"   Current:  {current_hash}")
            return False

        # Check if file count changed significantly (>10%)
        if previous_count > 0:
            count_change_pct = abs(current_count - previous_count) / previous_count
            if count_change_pct > 0.10:  # 10% threshold
                logger.info(f"Cannot skip {self.name}: file count changed by {count_change_pct*100:.1f}%")
                logger.info(f"   Previous: {previous_count}")
                logger.info(f"   Current:  {current_count}")
                return False

        # All validations passed - safe to skip
        logger.info(f"Skipping {self.name}: output valid and directory unchanged")
        return True

    def get_dependencies(self) -> list:
        """
        No dependencies - can run independently.

        Returns:
            Empty list (no dependencies)
        """
        return []

    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate that processing directory exists.

        Args:
            context: Pipeline context

        Returns:
            bool: True if prerequisites satisfied
        """
        if not context.processing_dir.exists():
            logger.error(f"Processing directory does not exist: {context.processing_dir}")
            return False
        return True
