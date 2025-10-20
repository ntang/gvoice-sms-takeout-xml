"""
Attachment Copying Stage - Phase 2 of Pipeline Architecture

This stage copies attachments from the processing directory to the output directory,
preserving the directory structure and implementing resumability.

Features:
- Copies attachments based on attachment_mapping.json
- Preserves directory structure (Calls/, Voicemails/, etc.)
- Implements resumability (skips already-copied files)
- Tracks copied files for idempotency
- Handles errors gracefully (missing files, permissions, disk space)

Dependencies: attachment_mapping stage (requires attachment_mapping.json)

Author: Claude Code
Date: 2025-10-20
"""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Set

from core.pipeline.base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class AttachmentCopyingStage(PipelineStage):
    """
    Pipeline stage that copies attachments from processing_dir to output_dir.

    Input:
        - attachment_mapping.json (from attachment_mapping stage)
        - Source files in processing_dir

    Output:
        - Copied files in output_dir/attachments/
        - Preserves directory structure

    Resumability:
        - Tracks copied files in pipeline state
        - Skips already-copied files on rerun
        - Can resume after interruption
    """

    def __init__(self):
        """Initialize the attachment copying stage."""
        super().__init__("attachment_copying")

    def get_dependencies(self) -> List[str]:
        """Return list of stage names this stage depends on."""
        return ["attachment_mapping"]

    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate that prerequisites are met.

        Required:
            - attachment_mapping.json exists in output_dir

        Args:
            context: Pipeline context with processing and output directories

        Returns:
            True if prerequisites met, False otherwise
        """
        mapping_file = context.output_dir / "attachment_mapping.json"

        if not mapping_file.exists():
            logger.error(f"❌ Prerequisite failed: {mapping_file} does not exist")
            logger.error("   Run 'attachment-mapping' stage first")
            return False

        return True

    def can_skip(self, context: PipelineContext) -> bool:
        """
        Determine if stage can be skipped (smart caching).

        Skip if:
            - Stage has completed before
            - Attachments directory exists
            - All files from previous run still present
            - Mapping file count unchanged

        Args:
            context: Pipeline context with state data

        Returns:
            True if stage can be safely skipped, False otherwise
        """
        # 1. Did stage ever complete?
        if not context.has_stage_completed(self.name):
            logger.debug("Cannot skip: stage never completed")
            return False

        # 2. Does attachments directory exist?
        attachments_dir = context.output_dir / "attachments"
        if not attachments_dir.exists():
            logger.debug("Cannot skip: attachments directory missing")
            return False

        # 3. Load current mapping to check file count
        mapping_file = context.output_dir / "attachment_mapping.json"
        if not mapping_file.exists():
            logger.debug("Cannot skip: mapping file missing")
            return False

        try:
            with open(mapping_file, 'r') as f:
                mapping_data = json.load(f)

            current_total = mapping_data['metadata']['total_mappings']
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Cannot skip: error reading mapping file: {e}")
            return False

        # 4. Check if file count changed
        stage_data = context.get_stage_data(self.name)
        if stage_data:
            previous_total = stage_data.get('total_copied', 0) + stage_data.get('total_skipped', 0)

            if current_total != previous_total:
                logger.debug(f"Cannot skip: file count changed ({previous_total} → {current_total})")
                return False

            # 5. Verify all previously copied files still exist
            copied_files = stage_data.get('copied_files', [])
            for file_path in copied_files:
                dest_file = attachments_dir / file_path
                if not dest_file.exists():
                    logger.debug(f"Cannot skip: previously copied file missing: {file_path}")
                    return False

        logger.debug("Can skip: all validation checks passed")
        return True

    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute attachment copying.

        Process:
            1. Load attachment_mapping.json
            2. Create output attachments directory
            3. Copy each file, preserving directory structure
            4. Track copied/skipped/errored files
            5. Return result with metadata

        Args:
            context: Pipeline context

        Returns:
            StageResult with success status, counts, and metadata
        """
        start_time = time.time()

        logger.info("🔍 Starting attachment copying...")

        try:
            # Load attachment mapping
            mapping_file = context.output_dir / "attachment_mapping.json"
            with open(mapping_file, 'r') as f:
                mapping_data = json.load(f)

            mappings = mapping_data['mappings']
            total_mappings = len(mappings)

            logger.info(f"   Mappings to process: {total_mappings}")

            # Create output attachments directory
            attachments_dir = context.output_dir / "attachments"
            attachments_dir.mkdir(exist_ok=True)

            # Track results
            copied_files: List[str] = []
            skipped_files: List[str] = []
            errors: List[str] = []

            # Copy each file
            for src_ref, file_info in mappings.items():
                filename = file_info['filename']  # e.g., "Calls/photo.jpg"
                source_path = Path(file_info['source_path'])

                # Destination path preserves directory structure
                dest_path = attachments_dir / filename

                # Skip if already copied
                if dest_path.exists():
                    skipped_files.append(filename)
                    continue

                # Copy file
                try:
                    # Create parent directories if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Check if source exists
                    if not source_path.exists():
                        error_msg = f"Source file not found: {filename}"
                        logger.warning(f"   ⚠️  {error_msg}")
                        errors.append(error_msg)
                        continue

                    # Copy with metadata preservation
                    shutil.copy2(source_path, dest_path)
                    copied_files.append(filename)

                except PermissionError as e:
                    error_msg = f"Permission denied copying {filename}: {e}"
                    logger.warning(f"   ⚠️  {error_msg}")
                    errors.append(error_msg)

                except OSError as e:
                    error_msg = f"OS error copying {filename}: {e}"
                    logger.warning(f"   ⚠️  {error_msg}")
                    errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Unexpected error copying {filename}: {e}"
                    logger.error(f"   ❌ {error_msg}")
                    errors.append(error_msg)

            # Calculate totals
            total_copied = len(copied_files)
            total_skipped = len(skipped_files)
            total_errors = len(errors)
            total_processed = total_copied + total_skipped

            elapsed_time = time.time() - start_time

            logger.info(f"✅ Attachment copying completed in {elapsed_time:.2f}s")
            logger.info(f"   📊 Total processed: {total_processed}")
            logger.info(f"   📋 Copied: {total_copied}")
            logger.info(f"   ⏭️  Skipped: {total_skipped}")
            logger.info(f"   ⚠️  Errors: {total_errors}")
            logger.info(f"   💾 Output: {attachments_dir}")

            # Build metadata
            metadata = {
                'total_copied': total_copied,
                'total_skipped': total_skipped,
                'total_errors': total_errors,
                'output_dir': str(attachments_dir),
                'copied_files': copied_files
            }

            return StageResult(
                success=True,
                records_processed=total_processed,
                metadata=metadata,
                errors=errors,
                execution_time=elapsed_time
            )

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse attachment_mapping.json: {e}"
            logger.error(f"❌ {error_msg}")
            return StageResult(
                success=False,
                records_processed=0,
                metadata={},
                errors=[error_msg],
                execution_time=time.time() - start_time
            )

        except Exception as e:
            error_msg = f"Attachment copying failed: {e}"
            logger.error(f"❌ {error_msg}")
            return StageResult(
                success=False,
                records_processed=0,
                metadata={},
                errors=[error_msg],
                execution_time=time.time() - start_time
            )
