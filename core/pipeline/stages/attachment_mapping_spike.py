"""
SPIKE: Attachment Mapping Stage - Proof of Concept

This is a quick spike to validate the approach before committing to full TDD.
NOT production code - for exploration only.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Tuple

from ..base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class AttachmentMappingStage(PipelineStage):
    """SPIKE: Maps HTML src attributes to attachment filenames."""

    def __init__(self):
        super().__init__("attachment_mapping_spike")

    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute attachment mapping stage.

        Args:
            context: Pipeline context

        Returns:
            StageResult: Mapping results
        """
        start_time = time.time()

        try:
            logger.info("🔍 SPIKE: Starting attachment mapping...")

            # Use existing optimized function
            from core.performance_optimizations import build_attachment_mapping_optimized

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
                    "processing_dir": str(context.processing_dir)
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

            logger.info(f"✅ SPIKE: Attachment mapping completed in {execution_time:.2f}s")
            logger.info(f"   📊 Total mappings: {len(src_filename_map)}")
            logger.info(f"   💾 Saved to: {output_file}")

            return StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=len(src_filename_map),
                output_files=[output_file],
                metadata={
                    "total_mappings": len(src_filename_map),
                    "output_file": str(output_file)
                }
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ SPIKE: Attachment mapping failed: {e}", exc_info=True)

            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"Attachment mapping failed: {str(e)}"]
            )

    def get_dependencies(self) -> list:
        """No dependencies - can run independently."""
        return []

    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """Validate that processing directory exists."""
        if not context.processing_dir.exists():
            logger.error(f"Processing directory does not exist: {context.processing_dir}")
            return False
        return True
