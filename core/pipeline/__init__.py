"""
Pipeline Architecture Module

This module provides a modular, rerunnable pipeline system for SMS processing.
Each stage can be executed independently, with state persistence between stages.
"""

from .base import PipelineStage, PipelineContext, StageResult
from .manager import PipelineManager
from .state import StateManager

__all__ = [
    'PipelineStage',
    'PipelineContext', 
    'StageResult',
    'PipelineManager',
    'StateManager'
]
