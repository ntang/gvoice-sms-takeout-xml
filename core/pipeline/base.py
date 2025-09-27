"""
Base classes for pipeline architecture.

Defines the core interfaces and data structures for the modular pipeline system.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result of executing a pipeline stage."""
    success: bool
    execution_time: float
    records_processed: int
    output_files: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error)
        
    def add_output_file(self, file_path: Path) -> None:
        """Add an output file to the result."""
        self.output_files.append(file_path)
        
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for the stage result."""
        self.metadata[key] = value


@dataclass 
class PipelineContext:
    """Context passed between pipeline stages."""
    processing_dir: Path
    output_dir: Path
    config: Optional[Any] = None  # ProcessingConfig - avoiding circular import
    stage_state: Dict[str, Any] = field(default_factory=dict)
    pipeline_start_time: datetime = field(default_factory=datetime.now)
    
    def get_stage_data(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """Get data stored by a previous stage."""
        return self.stage_state.get(stage_name)
        
    def set_stage_data(self, stage_name: str, data: Dict[str, Any]) -> None:
        """Store data for use by subsequent stages."""
        self.stage_state[stage_name] = data
        
    def has_stage_completed(self, stage_name: str) -> bool:
        """Check if a stage has completed successfully."""
        stage_data = self.get_stage_data(stage_name)
        return stage_data is not None and stage_data.get('completed', False)


class PipelineStage(ABC):
    """Abstract base class for all pipeline stages."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute the pipeline stage.
        
        Args:
            context: Pipeline context with configuration and state
            
        Returns:
            StageResult: Result of stage execution
        """
        pass
    
    def can_skip(self, context: PipelineContext) -> bool:
        """
        Check if this stage can be skipped (already completed).
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if stage can be skipped
        """
        return context.has_stage_completed(self.name)
    
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate that prerequisites for this stage are met.
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if prerequisites are satisfied
        """
        # Base implementation - no prerequisites
        return True
        
    def get_dependencies(self) -> List[str]:
        """
        Get list of stage names that must complete before this stage.
        
        Returns:
            List[str]: Stage names this stage depends on
        """
        return []
        
    def cleanup_on_error(self, context: PipelineContext, error: Exception) -> None:
        """
        Cleanup any partial work if stage execution fails.
        
        Args:
            context: Pipeline context
            error: Exception that caused the failure
        """
        # Base implementation - no cleanup needed
        pass
        
    def get_stage_info(self) -> Dict[str, Any]:
        """
        Get information about this stage for status reporting.
        
        Returns:
            Dict containing stage information
        """
        return {
            'name': self.name,
            'dependencies': self.get_dependencies(),
            'description': self.__doc__ or f"{self.name} pipeline stage"
        }
