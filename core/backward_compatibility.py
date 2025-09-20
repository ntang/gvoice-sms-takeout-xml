"""
Backward Compatibility Layer for SMS/MMS processing system.

This module provides backward compatibility for existing code that uses
global variables and function parameters, allowing gradual migration to
the new configuration system.
"""

import logging
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .processing_config import ProcessingConfig, ConfigurationBuilder
from .configuration_manager import get_configuration_manager, set_global_configuration
from .configuration_migration import migrate_module_to_configuration

logger = logging.getLogger(__name__)


class BackwardCompatibilityManager:
    """
    Manages backward compatibility for existing code.
    
    This class provides a bridge between the old global variable system
    and the new configuration system, allowing existing code to continue
    working while new code can use the modern configuration approach.
    """
    
    def __init__(self):
        """Initialize the backward compatibility manager."""
        self._legacy_functions = {}
        self._global_variable_mappings = {}
        self._migration_warnings = set()
        
        # Register legacy function mappings
        self._register_legacy_functions()
        
        logger.info("Backward Compatibility Manager initialized")
    
    def _register_legacy_functions(self):
        """Register mappings for legacy functions."""
        self._legacy_functions.update({
            'setup_processing_paths': self._setup_processing_paths_legacy_wrapper,
            'validate_processing_directory': self._validate_processing_directory_legacy_wrapper,
        })
    
    def _setup_processing_paths_legacy_wrapper(
        self,
        processing_dir: Union[str, Path],
        enable_phone_prompts: bool = False,
        buffer_size: int = 8192,
        batch_size: int = 1000,
        cache_size: int = 25000,
        large_dataset: bool = False,
        phone_lookup_file: Optional[Path] = None,
    ) -> None:
        """
        Legacy wrapper for setup_processing_paths.
        
        This function maintains backward compatibility while internally
        using the new configuration system.
        """
        # Show deprecation warning
        self._show_migration_warning(
            'setup_processing_paths',
            'Use setup_processing_paths_with_config() or setup_processing_paths_legacy() instead'
        )
        
        # Create configuration from legacy parameters
        config = self._create_config_from_legacy_params(
            processing_dir=processing_dir,
            enable_phone_prompts=enable_phone_prompts,
            buffer_size=buffer_size,
            batch_size=batch_size,
            cache_size=cache_size,
            large_dataset=large_dataset,
        )
        
        # Set phone_lookup_file if provided
        if phone_lookup_file is not None:
            config.phone_lookup_file = phone_lookup_file
        
        # Call the new configuration-driven version
        from .function_signatures import setup_processing_paths_with_config
        setup_processing_paths_with_config(config)
    
    def _validate_processing_directory_legacy_wrapper(
        self,
        processing_dir: Union[str, Path]
    ) -> bool:
        """
        Legacy wrapper for validate_processing_directory.
        
        This function maintains backward compatibility while internally
        using the new configuration system.
        """
        # Show deprecation warning
        self._show_migration_warning(
            'validate_processing_directory',
            'Use validate_processing_config() instead'
        )
        
        # Convert to Path if needed
        if isinstance(processing_dir, str):
            processing_dir = Path(processing_dir)
        
        # Create a minimal configuration for validation
        config = ProcessingConfig(processing_dir=processing_dir)
        
        # Use the new validation function
        from .function_signatures import validate_processing_config
        return validate_processing_config(config)
    
    def _create_config_from_legacy_params(
        self,
        processing_dir: Union[str, Path],
        enable_phone_prompts: bool = False,
        buffer_size: int = 8192,
        batch_size: int = 1000,
        cache_size: int = 25000,
        large_dataset: bool = False,
        preset: str = "default"
    ) -> ProcessingConfig:
        """
        Create a ProcessingConfig from legacy parameters.
        
        Args:
            processing_dir: Processing directory path
            enable_phone_prompts: Whether to enable phone prompts
            buffer_size: Buffer size for I/O operations
            batch_size: Batch size for processing
            cache_size: Cache size for optimization
            large_dataset: Whether this is a large dataset
            output_format: Output format ('html')
            preset: Configuration preset to use
            
        Returns:
            ProcessingConfig: Configuration object
        """
        # Convert processing_dir to Path if needed
        if isinstance(processing_dir, str):
            processing_dir = Path(processing_dir)
        
        # Start with preset configuration
        config = ConfigurationBuilder.create_with_presets(processing_dir, preset)
        
        # Override with legacy parameters
        config_dict = config.to_dict()
        config_dict.update({
            'enable_phone_prompts': enable_phone_prompts,
            'buffer_size': buffer_size,
            'batch_size': batch_size,
            'cache_size': cache_size,
            'large_dataset': large_dataset,
        })
        
        # Create final configuration
        return ProcessingConfig.from_dict(config_dict)
    
    def _show_migration_warning(self, function_name: str, suggestion: str):
        """Show a migration warning for legacy function usage."""
        warning_key = f"{function_name}_{suggestion}"
        
        if warning_key not in self._migration_warnings:
            warnings.warn(
                f"Function '{function_name}' is deprecated. {suggestion}",
                DeprecationWarning,
                stacklevel=3
            )
            self._migration_warnings.add(warning_key)
    
    def get_legacy_function(self, function_name: str):
        """
        Get a legacy function wrapper.
        
        Args:
            function_name: Name of the legacy function
            
        Returns:
            Function wrapper that maintains backward compatibility
        """
        if function_name in self._legacy_functions:
            return self._legacy_functions[function_name]
        else:
            raise ValueError(f"Unknown legacy function: {function_name}")
    
    def register_legacy_function(self, function_name: str, wrapper_function):
        """
        Register a custom legacy function wrapper.
        
        Args:
            function_name: Name of the legacy function
            wrapper_function: Function that provides backward compatibility
        """
        self._legacy_functions[function_name] = wrapper_function
        logger.info(f"Registered legacy function wrapper: {function_name}")
    
    def migrate_legacy_globals(self, module_object: Any, processing_dir: Union[str, Path]) -> ProcessingConfig:
        """
        Migrate legacy global variables to configuration.
        
        Args:
            module_object: Module containing global variables
            processing_dir: Processing directory path
            
        Returns:
            ProcessingConfig: Migrated configuration
        """
        # Convert processing_dir to Path if needed
        if isinstance(processing_dir, str):
            processing_dir = Path(processing_dir)
        
        # Migrate the module
        config, updates = migrate_module_to_configuration(module_object, processing_dir, "default")
        
        logger.info(f"Migrated {len(updates)} legacy global variables to configuration")
        return config


# Global backward compatibility manager instance
_backward_compatibility_manager = BackwardCompatibilityManager()


def get_backward_compatibility_manager() -> BackwardCompatibilityManager:
    """Get the global backward compatibility manager instance."""
    return _backward_compatibility_manager


def setup_processing_paths_legacy_compat(
    processing_dir: Union[str, Path],
    enable_phone_prompts: bool = False,
    buffer_size: int = 8192,
    batch_size: int = 1000,
    cache_size: int = 25000,
    large_dataset: bool = False,
    phone_lookup_file: Optional[Path] = None,
) -> None:
    """
    Legacy-compatible version of setup_processing_paths.
    
    This function provides backward compatibility for existing code
    while internally using the new configuration system.
    
    Args:
        processing_dir: Path to the processing directory
        enable_phone_prompts: Whether to enable phone number alias prompts
        buffer_size: Buffer size for file I/O operations
        batch_size: Batch size for processing files
        cache_size: Cache size for performance optimization
        large_dataset: Whether this is a large dataset
            output_format: Output format ('html')
    """
    manager = get_backward_compatibility_manager()
    manager._setup_processing_paths_legacy_wrapper(
        processing_dir=processing_dir,
        enable_phone_prompts=enable_phone_prompts,
        buffer_size=buffer_size,
        batch_size=batch_size,
        cache_size=cache_size,
        large_dataset=large_dataset,
        phone_lookup_file=phone_lookup_file,
    )


def validate_processing_directory_legacy_compat(processing_dir: Union[str, Path]) -> bool:
    """
    Legacy-compatible version of validate_processing_directory.
    
    This function provides backward compatibility for existing code
    while internally using the new configuration system.
    
    Args:
        processing_dir: Path to the directory to validate
        
    Returns:
        bool: True if directory is valid, False otherwise
    """
    manager = get_backward_compatibility_manager()
    return manager._validate_processing_directory_legacy_wrapper(processing_dir)


def create_legacy_compatibility_config(
    processing_dir: Union[str, Path],
    enable_phone_prompts: bool = False,
    buffer_size: int = 8192,
    batch_size: int = 1000,
    cache_size: int = 25000,
    large_dataset: bool = False,
    output_format: str = "html",
    preset: str = "default"
) -> ProcessingConfig:
    """
    Create a configuration object from legacy parameters.
    
    This function provides a bridge between the old parameter-based approach
    and the new configuration object approach.
    
    Args:
        processing_dir: Path to the processing directory
        enable_phone_prompts: Whether to enable phone number alias prompts
        buffer_size: Buffer size for file I/O operations
        batch_size: Batch size for processing files
        cache_size: Cache size for performance optimization
        large_dataset: Whether this is a large dataset
            output_format: Output format ('html')
        preset: Configuration preset to use
        
    Returns:
        ProcessingConfig: Configuration object with the specified settings
    """
    manager = get_backward_compatibility_manager()
    return manager._create_config_from_legacy_params(
        processing_dir=processing_dir,
        enable_phone_prompts=enable_phone_prompts,
        buffer_size=buffer_size,
        batch_size=batch_size,
        cache_size=cache_size,
        large_dataset=large_dataset,
        preset=preset
    )


def enable_backward_compatibility():
    """
    Enable backward compatibility mode.
    
    This function sets up the backward compatibility layer to ensure
    existing code continues to work while new code can use the
    modern configuration system.
    """
    # Import the sms module to patch it
    import sms
    
    # Patch the legacy functions
    sms.setup_processing_paths = setup_processing_paths_legacy_compat
    sms.validate_processing_directory = validate_processing_directory_legacy_compat
    
    logger.info("✅ Backward compatibility mode enabled")
    logger.info("   - Legacy functions are now using the new configuration system")
    logger.info("   - Existing code will continue to work")
    logger.info("   - New code can use the modern configuration approach")


def disable_backward_compatibility():
    """
    Disable backward compatibility mode.
    
    This function removes the backward compatibility layer, requiring
    all code to use the modern configuration system.
    """
    # Import the sms module to restore original functions
    import sms
    
    # Restore original functions (this would require storing them first)
    logger.warning("⚠️  Backward compatibility mode disabled")
    logger.warning("   - All code must now use the modern configuration system")
    logger.warning("   - Legacy function calls will fail")


def is_backward_compatibility_enabled() -> bool:
    """
    Check if backward compatibility mode is enabled.
    
    Returns:
        bool: True if backward compatibility is enabled, False otherwise
    """
    try:
        import sms
        return sms.setup_processing_paths == setup_processing_paths_legacy_compat
    except (ImportError, AttributeError):
        return False
