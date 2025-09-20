"""
Configuration Migration Utilities for SMS/MMS processing system.

Provides utilities for migrating from the old global variable system
to the new configuration system while maintaining backward compatibility.
"""

import logging
import inspect
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from .configuration_manager import get_configuration_manager, set_global_configuration
from .processing_config import ProcessingConfig, ConfigurationBuilder

logger = logging.getLogger(__name__)


class ConfigurationMigrationHelper:
    """
    Helper class for migrating from global variables to configuration objects.
    
    This class provides utilities for identifying global variables,
    mapping them to configuration fields, and creating migration paths.
    """
    
    def __init__(self):
        """Initialize the migration helper."""
        self._global_variable_mapping = {
            # Core processing settings
            'ENABLE_PHONE_PROMPTS': 'enable_phone_prompts',
            'ENABLE_TEST_MODE': 'test_mode',
            'TEST_LIMIT': 'test_limit',
            'OUTPUT_FORMAT': 'output_format',
            'PROCESSING_DIR': 'processing_dir',
            'OUTPUT_DIR': 'output_dir',
            
            # Performance settings
            'MAX_WORKERS': 'max_workers',
            'CHUNK_SIZE': 'chunk_size',
            'BATCH_SIZE': 'batch_size',
            'BUFFER_SIZE': 'buffer_size',
            'CACHE_SIZE': 'cache_size',
            'MEMORY_THRESHOLD': 'memory_threshold',
            
            # Feature flags - performance settings now hardcoded
            # 'ENABLE_PARALLEL_PROCESSING': 'enable_parallel_processing',  # Removed - hardcoded
            # 'ENABLE_STREAMING_PARSING': 'enable_streaming_parsing',  # Removed - hardcoded
            # 'ENABLE_MMAP_FOR_LARGE_FILES': 'enable_mmap_for_large_files',  # Removed - hardcoded
            # 'ENABLE_PERFORMANCE_MONITORING': 'enable_performance_monitoring',  # Removed - hardcoded
            # 'ENABLE_PROGRESS_LOGGING': 'enable_progress_logging',  # Removed - hardcoded
            
            # Validation settings
            'ENABLE_PATH_VALIDATION': 'enable_path_validation',
            'ENABLE_RUNTIME_VALIDATION': 'enable_runtime_validation',
            'STRICT_MODE': 'strict_mode',
            
            # Phone lookup settings
            'SKIP_FILTERED_CONTACTS': 'skip_filtered_contacts',
            
            # Filtering settings
            'INCLUDE_SERVICE_CODES': 'include_service_codes',
            'FILTER_NUMBERS_WITHOUT_ALIASES': 'filter_numbers_without_aliases',
            'FILTER_NON_PHONE_NUMBERS': 'filter_non_phone_numbers',
            
            # Debug settings
            'LOG_LEVEL': 'log_level',
            'VERBOSE': 'verbose',
            'DEBUG': 'debug',
            'DEBUG_ATTACHMENTS': 'debug_attachments',
            'DEBUG_PATHS': 'debug_paths',
            
            # Large dataset optimizations
            'LARGE_DATASET': 'large_dataset',
            # Batch processing is now always enabled
        }
        
        # Reverse mapping for configuration to global variables
        self._reverse_mapping = {v: k for k, v in self._global_variable_mapping.items()}
        
        logger.info("Configuration Migration Helper initialized")
    
    def get_global_variable_mapping(self) -> Dict[str, str]:
        """Get the mapping from global variables to configuration fields."""
        return self._global_variable_mapping.copy()
    
    def get_reverse_mapping(self) -> Dict[str, str]:
        """Get the reverse mapping from configuration fields to global variables."""
        return self._reverse_mapping.copy()
    
    def map_global_variable(self, global_var: str) -> Optional[str]:
        """Map a global variable name to its configuration field."""
        return self._global_variable_mapping.get(global_var)
    
    def map_configuration_field(self, config_field: str) -> Optional[str]:
        """Map a configuration field to its global variable name."""
        return self._reverse_mapping.get(config_field)
    
    def get_migratable_globals(self) -> List[str]:
        """Get list of global variables that can be migrated."""
        return list(self._global_variable_mapping.keys())
    
    def get_migratable_config_fields(self) -> List[str]:
        """Get list of configuration fields that can be migrated."""
        return list(self._reverse_mapping.keys())
    
    def create_migration_config(
        self,
        module_object: Any,
        processing_dir: Path,
        preset: str = "default"
    ) -> ProcessingConfig:
        """
        Create a configuration object from existing global variables.
        
        Args:
            module_object: Module containing global variables
            processing_dir: Processing directory path
            preset: Preset name to use as base
            
        Returns:
            ProcessingConfig: Configuration object with values from globals
        """
        # Start with preset configuration
        config = ConfigurationBuilder.create_with_presets(processing_dir, preset)
        
        # Override with global variable values
        migration_updates = {}
        
        for global_var, config_field in self._global_variable_mapping.items():
            if hasattr(module_object, global_var):
                global_value = getattr(module_object, global_var)
                
                # Only update if the global variable has a meaningful value
                if global_value is not None and global_value != "":
                    migration_updates[config_field] = global_value
                    logger.debug(f"Migrating {global_var}={global_value} -> {config_field}")
        
        # Apply migration updates
        if migration_updates:
            config_dict = config.to_dict()
            config_dict.update(migration_updates)
            config = ProcessingConfig.from_dict(config_dict)
            logger.info(f"Migrated {len(migration_updates)} global variables to configuration")
        
        return config
    
    def create_global_variable_updates(
        self,
        config: ProcessingConfig
    ) -> Dict[str, Any]:
        """
        Create updates for global variables from configuration.
        
        Args:
            config: Configuration object
            
        Returns:
            Dict mapping global variable names to values
        """
        updates = {}
        config_dict = config.to_dict()
        
        for config_field, global_var in self._reverse_mapping.items():
            if config_field in config_dict:
                config_value = config_dict[config_field]
                updates[global_var] = config_value
                logger.debug(f"Updating global {global_var} = {config_value} from {config_field}")
        
        return updates
    
    def apply_global_variable_updates(
        self,
        module_object: Any,
        updates: Dict[str, Any]
    ) -> None:
        """
        Apply global variable updates to a module.
        
        Args:
            module_object: Module to update
            updates: Dictionary of global variable updates
        """
        for global_var, value in updates.items():
            if hasattr(module_object, global_var):
                old_value = getattr(module_object, global_var)
                setattr(module_object, global_var, value)
                logger.debug(f"Updated {global_var}: {old_value} -> {value}")
            else:
                # Create new global variable
                setattr(module_object, global_var, value)
                logger.debug(f"Created new global variable {global_var} = {value}")
    
    def validate_migration(self, module_object: Any, config: ProcessingConfig) -> Dict[str, Any]:
        """
        Validate that migration was successful.
        
        Args:
            module_object: Module containing global variables
            config: Configuration object used for migration
            
        Returns:
            Dict containing validation results
        """
        validation_results = {
            'success': True,
            'errors': [],
            'warnings': [],
            'migrated_variables': [],
            'missing_variables': [],
            'value_mismatches': []
        }
        
        for global_var, config_field in self._global_variable_mapping.items():
            if hasattr(module_object, global_var):
                global_value = getattr(module_object, global_var)
                config_value = getattr(config, config_field, None)
                
                if global_value is not None and global_value != "":
                    validation_results['migrated_variables'].append(global_var)
                    
                    # Check for value mismatches
                    if global_value != config_value:
                        validation_results['value_mismatches'].append({
                            'global_var': global_var,
                            'global_value': global_value,
                            'config_value': config_value
                        })
                        validation_results['warnings'].append(
                            f"Value mismatch for {global_var}: {global_value} != {config_value}"
                        )
            else:
                validation_results['missing_variables'].append(global_var)
        
        if validation_results['value_mismatches']:
            validation_results['success'] = False
        
        return validation_results
    
    def generate_migration_report(
        self,
        module_object: Any,
        config: ProcessingConfig
    ) -> str:
        """
        Generate a human-readable migration report.
        
        Args:
            module_object: Module containing global variables
            config: Configuration object used for migration
            
        Returns:
            String containing the migration report
        """
        validation = self.validate_migration(module_object, config)
        
        report_lines = [
            "Configuration Migration Report",
            "=" * 40,
            f"Module: {module_object.__name__ if hasattr(module_object, '__name__') else str(type(module_object))}",
            f"Configuration: {config.processing_dir}",
            f"Migration Status: {'SUCCESS' if validation['success'] else 'PARTIAL'}",
            "",
            f"Migrated Variables: {len(validation['migrated_variables'])}",
            f"Missing Variables: {len(validation['missing_variables'])}",
            f"Value Mismatches: {len(validation['value_mismatches'])}",
            ""
        ]
        
        if validation['migrated_variables']:
            report_lines.append("Successfully Migrated Variables:")
            for var in validation['migrated_variables']:
                report_lines.append(f"  ✓ {var}")
            report_lines.append("")
        
        if validation['missing_variables']:
            report_lines.append("Missing Variables (not found in module):")
            for var in validation['missing_variables']:
                report_lines.append(f"  - {var}")
            report_lines.append("")
        
        if validation['value_mismatches']:
            report_lines.append("Value Mismatches (global != config):")
            for mismatch in validation['value_mismatches']:
                report_lines.append(
                    f"  ! {mismatch['global_var']}: "
                    f"{mismatch['global_value']} != {mismatch['config_value']}"
                )
            report_lines.append("")
        
        if validation['warnings']:
            report_lines.append("Warnings:")
            for warning in validation['warnings']:
                report_lines.append(f"  ⚠ {warning}")
            report_lines.append("")
        
        if validation['errors']:
            report_lines.append("Errors:")
            for error in validation['errors']:
                report_lines.append(f"  ✗ {error}")
        
        return "\n".join(report_lines)


def get_migration_helper() -> ConfigurationMigrationHelper:
    """Get the global migration helper instance."""
    return ConfigurationMigrationHelper()


def migrate_module_to_configuration(
    module_object: Any,
    processing_dir: Union[str, Path],
    preset: str = "default"
) -> Tuple[ProcessingConfig, Dict[str, Any]]:
    """
    Migrate a module from global variables to configuration.
    
    Args:
        module_object: Module containing global variables
        processing_dir: Processing directory path
        preset: Preset name to use as base
        
    Returns:
        Tuple of (ProcessingConfig, migration_updates)
    """
    helper = get_migration_helper()
    
    # Create configuration from global variables
    config = helper.create_migration_config(module_object, processing_dir, preset)
    
    # Create global variable updates
    updates = helper.create_global_variable_updates(config)
    
    # Apply updates to module
    helper.apply_global_variable_updates(module_object, updates)
    
    # Set as global configuration
    set_global_configuration(config)
    
    # Generate and log migration report
    report = helper.generate_migration_report(module_object, config)
    logger.info(f"Migration completed:\n{report}")
    
    return config, updates


def validate_module_migration(
    module_object: Any,
    config: ProcessingConfig
) -> Dict[str, Any]:
    """
    Validate that module migration was successful.
    
    Args:
        module_object: Module containing global variables
        config: Configuration object used for migration
        
    Returns:
        Dict containing validation results
    """
    helper = get_migration_helper()
    return helper.validate_migration(module_object, config)


def generate_migration_report(
    module_object: Any,
    config: ProcessingConfig
) -> str:
    """
    Generate a migration report for a module.
    
    Args:
        module_object: Module containing global variables
        config: Configuration object used for migration
        
    Returns:
        String containing the migration report
    """
    helper = get_migration_helper()
    return helper.generate_migration_report(module_object, config)
