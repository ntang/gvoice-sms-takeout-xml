"""
Migration Feature Flags for Architecture Improvement.

This module provides feature flags to control the gradual migration from
global variable-based filtering to parameterized filtering system.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MigrationFlags:
    """
    Feature flags for controlling the migration from global to parameterized filtering.
    
    This allows for gradual rollout, A/B testing, and safe rollback if issues arise.
    """
    
    def __init__(self):
        """Initialize migration flags from environment variables and defaults."""
        self._flags = self._load_flags()
        self._log_flag_status()
    
    def _load_flags(self) -> Dict[str, Any]:
        """Load migration flags from environment variables with safe defaults."""
        return {
            # Core migration flags
            'use_parameterized_filtering': self._get_bool_env('GVOICE_USE_PARAMETERIZED_FILTERING', True),
            'validate_filtering_consistency': self._get_bool_env('GVOICE_VALIDATE_FILTERING_CONSISTENCY', True),
            'enable_filtering_comparison': self._get_bool_env('GVOICE_ENABLE_FILTERING_COMPARISON', False),
            
            # Safety flags
            'fallback_to_global_on_error': self._get_bool_env('GVOICE_FALLBACK_TO_GLOBAL_ON_ERROR', True),
            'log_filtering_differences': self._get_bool_env('GVOICE_LOG_FILTERING_DIFFERENCES', True),
            
            # Performance flags
            'enable_filtering_metrics': self._get_bool_env('GVOICE_ENABLE_FILTERING_METRICS', False),
            'max_validation_samples': self._get_int_env('GVOICE_MAX_VALIDATION_SAMPLES', 1000),
            
            # Migration phases
            'migration_phase': self._get_str_env('GVOICE_MIGRATION_PHASE', 'complete'),
            'enable_legacy_support': self._get_bool_env('GVOICE_ENABLE_LEGACY_SUPPORT', True),
        }
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with default."""
        value = os.environ.get(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable with default."""
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def _get_str_env(self, key: str, default: str) -> str:
        """Get string environment variable with default."""
        return os.environ.get(key, default)
    
    def _log_flag_status(self):
        """Log the current status of migration flags."""
        logger.info("Migration flags loaded:")
        for flag, value in self._flags.items():
            logger.info(f"  {flag}: {value}")
    
    @property
    def use_parameterized_filtering(self) -> bool:
        """Whether to use the new parameterized filtering system."""
        return self._flags['use_parameterized_filtering']
    
    @property
    def validate_filtering_consistency(self) -> bool:
        """Whether to validate that both filtering systems produce identical results."""
        return self._flags['validate_filtering_consistency']
    
    @property
    def enable_filtering_comparison(self) -> bool:
        """Whether to run both filtering systems and compare results."""
        return self._flags['enable_filtering_comparison']
    
    @property
    def fallback_to_global_on_error(self) -> bool:
        """Whether to fallback to global filtering if parameterized filtering fails."""
        return self._flags['fallback_to_global_on_error']
    
    @property
    def log_filtering_differences(self) -> bool:
        """Whether to log when filtering systems produce different results."""
        return self._flags['log_filtering_differences']
    
    @property
    def enable_filtering_metrics(self) -> bool:
        """Whether to collect and report filtering performance metrics."""
        return self._flags['enable_filtering_metrics']
    
    @property
    def max_validation_samples(self) -> int:
        """Maximum number of samples to validate for consistency checking."""
        return self._flags['max_validation_samples']
    
    @property
    def migration_phase(self) -> str:
        """Current migration phase: 'testing', 'partial', 'complete'."""
        return self._flags['migration_phase']
    
    @property
    def enable_legacy_support(self) -> bool:
        """Whether to maintain legacy global filtering support."""
        return self._flags['enable_legacy_support']
    
    def update_flag(self, flag_name: str, value: Any) -> None:
        """Update a migration flag at runtime (for testing)."""
        if flag_name in self._flags:
            old_value = self._flags[flag_name]
            self._flags[flag_name] = value
            logger.info(f"Migration flag updated: {flag_name} {old_value} -> {value}")
        else:
            logger.warning(f"Unknown migration flag: {flag_name}")
    
    def get_flag_summary(self) -> Dict[str, Any]:
        """Get a summary of all migration flags."""
        return self._flags.copy()
    
    def is_migration_complete(self) -> bool:
        """Check if the migration is complete and legacy code can be removed."""
        return (
            self.use_parameterized_filtering and
            not self.enable_filtering_comparison and
            not self.enable_legacy_support and
            self.migration_phase == 'complete'
        )


# Global instance for easy access
migration_flags = MigrationFlags()


def get_migration_flags() -> MigrationFlags:
    """Get the global migration flags instance."""
    return migration_flags


def reset_migration_flags() -> None:
    """Reset migration flags (useful for testing)."""
    global migration_flags
    migration_flags = MigrationFlags()
