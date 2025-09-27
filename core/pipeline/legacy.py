"""
Legacy Pipeline Wrapper

Wraps the existing monolithic conversion process as a single pipeline stage
to maintain backward compatibility during the transition period.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from ..pipeline import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class LegacyConversionStage(PipelineStage):
    """Wraps the existing conversion process as a pipeline stage."""
    
    def __init__(self):
        super().__init__("legacy_conversion")
        
    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute the legacy conversion process.
        
        Args:
            context: Pipeline context
            
        Returns:
            StageResult: Result of the legacy conversion
        """
        start_time = time.time()
        
        try:
            # Import the existing conversion function
            # This maintains the exact same behavior as before
            from sms import process_html_files_param
            
            logger.info("Executing legacy conversion process")
            
            # Execute the existing conversion logic
            # Note: We're using the existing function which expects the old parameter format
            stats = process_html_files_param(
                processing_dir=context.processing_dir,
                output_dir=context.output_dir,
                config=context.config
            )
            
            execution_time = time.time() - start_time
            
            # Extract metrics from stats if available
            records_processed = 0
            output_files = []
            
            if isinstance(stats, dict):
                records_processed = stats.get('total_messages', 0)
                # Try to find output files
                if context.output_dir.exists():
                    output_files = list(context.output_dir.glob("*.html"))
                    
            result = StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=records_processed,
                output_files=output_files,
                metadata={
                    'legacy_conversion': True,
                    'stats': stats
                }
            )
            
            logger.info(f"Legacy conversion completed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Legacy conversion failed: {e}", exc_info=True)
            
            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"Legacy conversion failed: {str(e)}"]
            )
            
    def get_dependencies(self) -> List[str]:
        """Legacy conversion has no dependencies."""
        return []
        
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate that prerequisites for legacy conversion are met.
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if prerequisites are satisfied
        """
        # Check that processing directory exists and contains files
        if not context.processing_dir.exists():
            logger.error(f"Processing directory does not exist: {context.processing_dir}")
            return False
            
        # Check for at least some HTML files to process
        html_files = list(context.processing_dir.rglob("*.html"))
        if not html_files:
            logger.warning(f"No HTML files found in processing directory: {context.processing_dir}")
            # Don't fail - maybe this is intentional
            
        return True
