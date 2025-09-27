"""
Pipeline Manager

Orchestrates execution of pipeline stages with dependency management,
error handling, and state persistence.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from .base import PipelineContext, PipelineStage, StageResult
from .state import StateManager

logger = logging.getLogger(__name__)


class PipelineManager:
    """Manages execution of pipeline stages."""
    
    def __init__(self, processing_dir: Path, output_dir: Path, state_dir: Optional[Path] = None):
        """
        Initialize pipeline manager.
        
        Args:
            processing_dir: Directory containing input files
            output_dir: Directory for output files
            state_dir: Directory for pipeline state (default: output_dir/pipeline_state)
        """
        self.processing_dir = Path(processing_dir)
        self.output_dir = Path(output_dir)
        
        if state_dir is None:
            state_dir = output_dir / "pipeline_state"
        self.state_dir = Path(state_dir)
        
        self.state_manager = StateManager(self.state_dir)
        self.stages: Dict[str, PipelineStage] = {}
        self.stage_order: List[str] = []
        
    def register_stage(self, stage: PipelineStage) -> None:
        """
        Register a pipeline stage.
        
        Args:
            stage: Pipeline stage to register
        """
        self.stages[stage.name] = stage
        if stage.name not in self.stage_order:
            self.stage_order.append(stage.name)
        logger.debug(f"Registered pipeline stage: {stage.name}")
        
    def register_stages(self, stages: List[PipelineStage]) -> None:
        """
        Register multiple pipeline stages.
        
        Args:
            stages: List of pipeline stages to register
        """
        for stage in stages:
            self.register_stage(stage)
            
    def validate_dependencies(self) -> List[str]:
        """
        Validate that all stage dependencies can be satisfied.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for stage_name, stage in self.stages.items():
            dependencies = stage.get_dependencies()
            
            for dep in dependencies:
                if dep not in self.stages:
                    errors.append(f"Stage '{stage_name}' depends on unknown stage '{dep}'")
                    
        # Check for circular dependencies
        if not errors:
            visited = set()
            rec_stack = set()
            
            def has_cycle(stage_name: str) -> bool:
                visited.add(stage_name)
                rec_stack.add(stage_name)
                
                stage = self.stages.get(stage_name)
                if stage:
                    for dep in stage.get_dependencies():
                        if dep not in visited:
                            if has_cycle(dep):
                                return True
                        elif dep in rec_stack:
                            return True
                            
                rec_stack.remove(stage_name)
                return False
                
            for stage_name in self.stages:
                if stage_name not in visited:
                    if has_cycle(stage_name):
                        errors.append("Circular dependency detected in pipeline stages")
                        break
                        
        return errors
        
    def get_execution_order(self, requested_stages: Optional[List[str]] = None) -> List[str]:
        """
        Get the correct execution order for stages based on dependencies.
        
        Args:
            requested_stages: Specific stages to execute (None for all)
            
        Returns:
            List of stage names in execution order
        """
        if requested_stages is None:
            requested_stages = list(self.stages.keys())
            
        # Build dependency graph
        remaining = set(requested_stages)
        ordered = []
        
        while remaining:
            # Find stages with no unmet dependencies
            ready = []
            for stage_name in remaining:
                stage = self.stages[stage_name]
                dependencies = stage.get_dependencies()
                
                unmet_deps = [dep for dep in dependencies if dep in remaining]
                if not unmet_deps:
                    ready.append(stage_name)
                    
            if not ready:
                # This shouldn't happen if validate_dependencies passed
                raise RuntimeError(f"Cannot resolve dependencies for remaining stages: {remaining}")
                
            # Sort ready stages by their position in stage_order for consistency
            ready.sort(key=lambda x: self.stage_order.index(x) if x in self.stage_order else len(self.stage_order))
            
            for stage_name in ready:
                ordered.append(stage_name)
                remaining.remove(stage_name)
                
        return ordered
        
    def create_context(self, config: Optional[object] = None) -> PipelineContext:
        """
        Create a pipeline context.
        
        Args:
            config: Processing configuration object
            
        Returns:
            PipelineContext: Context for pipeline execution
        """
        context = PipelineContext(
            processing_dir=self.processing_dir,
            output_dir=self.output_dir,
            config=config
        )
        
        # Populate context with completed stage information
        for stage_name in self.stages:
            if self.state_manager.is_stage_completed(stage_name):
                last_execution = self.state_manager.get_last_successful_execution(stage_name)
                if last_execution:
                    context.set_stage_data(stage_name, {
                        'completed': True,
                        'execution_time': last_execution.get('execution_time', 0),
                        'records_processed': last_execution.get('records_processed', 0),
                        'last_execution': last_execution.get('execution_end')
                    })
        
        return context
        
    def execute_stage(self, stage_name: str, context: PipelineContext, force: bool = False) -> StageResult:
        """
        Execute a single pipeline stage.
        
        Args:
            stage_name: Name of stage to execute
            context: Pipeline context
            force: Force execution even if stage can be skipped
            
        Returns:
            StageResult: Result of stage execution
        """
        if stage_name not in self.stages:
            raise ValueError(f"Unknown stage: {stage_name}")
            
        stage = self.stages[stage_name]
        
        # Check if stage can be skipped
        if not force and stage.can_skip(context):
            logger.info(f"Skipping stage '{stage_name}' - already completed")
            return StageResult(
                success=True,
                execution_time=0.0,
                records_processed=0,
                metadata={'skipped': True}
            )
            
        # Validate prerequisites
        if not stage.validate_prerequisites(context):
            error_msg = f"Prerequisites not met for stage '{stage_name}'"
            logger.error(error_msg)
            return StageResult(
                success=False,
                execution_time=0.0,
                records_processed=0,
                errors=[error_msg]
            )
            
        # Record stage start
        execution_id = self.state_manager.record_stage_start(stage_name)
        
        logger.info(f"Executing stage: {stage_name}")
        start_time = time.time()
        
        try:
            # Execute the stage
            result = stage.execute(context)
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            # Record completion in context if successful
            if result.success:
                context.set_stage_data(stage_name, {
                    'completed': True,
                    'execution_time': execution_time,
                    'records_processed': result.records_processed,
                    'output_files': [str(f) for f in result.output_files]
                })
                
            logger.info(f"Stage '{stage_name}' completed: success={result.success}, "
                       f"time={execution_time:.2f}s, records={result.records_processed}")
                       
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Stage '{stage_name}' failed with exception: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Cleanup on error
            try:
                stage.cleanup_on_error(context, e)
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed for stage '{stage_name}': {cleanup_error}")
                
            result = StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[error_msg]
            )
            
        # Record stage result
        self.state_manager.record_stage_result(execution_id, result)
        
        return result
        
    def execute_pipeline(self, 
                        stages: Optional[List[str]] = None,
                        config: Optional[object] = None,
                        force: bool = False,
                        stop_on_error: bool = True) -> Dict[str, StageResult]:
        """
        Execute the complete pipeline or specified stages.
        
        Args:
            stages: Specific stages to execute (None for all)
            config: Processing configuration
            force: Force execution of all stages
            stop_on_error: Stop pipeline on first error
            
        Returns:
            Dict mapping stage names to their results
        """
        # Validate dependencies
        validation_errors = self.validate_dependencies()
        if validation_errors:
            raise RuntimeError(f"Pipeline validation failed: {', '.join(validation_errors)}")
            
        # Get execution order
        execution_order = self.get_execution_order(stages)
        logger.info(f"Pipeline execution order: {' → '.join(execution_order)}")
        
        # Create context
        context = self.create_context(config)
        
        # Execute stages
        results = {}
        for stage_name in execution_order:
            result = self.execute_stage(stage_name, context, force)
            results[stage_name] = result
            
            if not result.success and stop_on_error:
                logger.error(f"Pipeline stopped due to stage failure: {stage_name}")
                break
                
        return results
        
    def get_status(self) -> Dict[str, any]:
        """
        Get current pipeline status.
        
        Returns:
            Dict with pipeline status information
        """
        return self.state_manager.get_pipeline_status()
        
    def reset_stage(self, stage_name: str) -> None:
        """
        Reset a specific stage's state.
        
        Args:
            stage_name: Name of stage to reset
        """
        if stage_name not in self.stages:
            raise ValueError(f"Unknown stage: {stage_name}")
            
        self.state_manager.clear_stage_state(stage_name)
        logger.info(f"Reset stage: {stage_name}")
        
    def reset_pipeline(self) -> None:
        """Reset the entire pipeline state."""
        self.state_manager.clear_all_state()
        logger.info("Reset complete pipeline state")
