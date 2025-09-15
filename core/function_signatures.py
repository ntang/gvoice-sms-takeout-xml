"""
Function Signature Updates for SMS/MMS processing system.

This module provides updated function signatures that accept ProcessingConfig
objects while maintaining backward compatibility with existing code.
"""

import logging
from pathlib import Path
from typing import Optional, Union

from .processing_config import ProcessingConfig
from .configuration_manager import get_configuration_manager, set_global_configuration
from .configuration_migration import migrate_module_to_configuration

logger = logging.getLogger(__name__)


def setup_processing_paths_with_config(
    config: ProcessingConfig,
    enable_phone_prompts: Optional[bool] = None,
    buffer_size: Optional[int] = None,
    batch_size: Optional[int] = None,
    cache_size: Optional[int] = None,
    large_dataset: Optional[bool] = None,
    output_format: Optional[str] = None,
    phone_lookup_file: Optional[Path] = None,
) -> None:
    """
    Set up all file paths based on the specified ProcessingConfig.
    
    This is the new configuration-driven version of setup_processing_paths.
    
    Args:
        config: ProcessingConfig object containing all settings
        enable_phone_prompts: Override phone prompts setting (optional)
        buffer_size: Override buffer size (optional)
        batch_size: Override batch size (optional)
        cache_size: Override cache size (optional)
        large_dataset: Override large dataset setting (optional)
        output_format: Override output format (optional)
        
    Raises:
        ValueError: If parameters are invalid
        TypeError: If parameter types are incorrect
    """
    # Set global configuration for other parts of the system
    set_global_configuration(config)
    
    # Use override values if provided, otherwise use config values
    effective_phone_prompts = enable_phone_prompts if enable_phone_prompts is not None else config.enable_phone_prompts
    effective_buffer_size = buffer_size if buffer_size is not None else config.buffer_size
    effective_batch_size = batch_size if batch_size is not None else config.batch_size
    effective_cache_size = cache_size if cache_size is not None else config.cache_size
    effective_large_dataset = large_dataset if large_dataset is not None else config.large_dataset
    effective_output_format = output_format if output_format is not None else config.output_format
    effective_phone_lookup_file = phone_lookup_file if phone_lookup_file is not None else config.phone_lookup_file
    
    # Call the original function with the effective values
    from sms import setup_processing_paths
    setup_processing_paths(
        processing_dir=config.processing_dir,
        enable_phone_prompts=effective_phone_prompts,
        buffer_size=effective_buffer_size,
        batch_size=effective_batch_size,
        cache_size=effective_cache_size,
        large_dataset=effective_large_dataset,
        output_format=effective_output_format,
        phone_lookup_file=effective_phone_lookup_file,
    )
    
    logger.info("✅ Processing paths initialized with configuration object")


def setup_processing_paths_legacy(
    processing_dir: Union[str, Path],
    enable_phone_prompts: bool = False,
    buffer_size: int = 8192,
    batch_size: int = 1000,
    cache_size: int = 25000,
    large_dataset: bool = False,
    output_format: str = "html",
    preset: str = "default",
) -> None:
    """
    Legacy version of setup_processing_paths for backward compatibility.
    
    This function creates a ProcessingConfig from the legacy parameters
    and then calls the new configuration-driven version.
    
    Args:
        processing_dir: Path to the processing directory
        enable_phone_prompts: Whether to enable phone number alias prompts
        buffer_size: Buffer size for file I/O operations
        batch_size: Batch size for processing files
        cache_size: Cache size for performance optimization
        large_dataset: Whether this is a large dataset
        output_format: Output format ('xml' or 'html')
        
    Raises:
        ValueError: If parameters are invalid
        TypeError: If parameter types are incorrect
    """
    # Convert processing_dir to Path if it's a string
    if isinstance(processing_dir, str):
        processing_dir = Path(processing_dir)
    
    # Create a ProcessingConfig from the legacy parameters with preset
    from .processing_config import ConfigurationBuilder
    config = ConfigurationBuilder.create_with_presets(processing_dir, preset)
    
    # Override with legacy parameters
    config_dict = config.to_dict()
    config_dict.update({
        'enable_phone_prompts': enable_phone_prompts,
        'buffer_size': buffer_size,
        'batch_size': batch_size,
        'cache_size': cache_size,
        'large_dataset': large_dataset,
        'output_format': output_format,
    })
    
    # Create final configuration
    from .processing_config import ProcessingConfig
    config = ProcessingConfig.from_dict(config_dict)
    
    # Call the new configuration-driven version
    setup_processing_paths_with_config(config)
    
    logger.info("✅ Processing paths initialized with legacy parameters (converted to config)")


def migrate_sms_module_to_configuration(
    processing_dir: Union[str, Path],
    preset: str = "default"
) -> ProcessingConfig:
    """
    Migrate the sms module from global variables to configuration.
    
    This function will:
    1. Create a ProcessingConfig from the specified processing directory
    2. Migrate any existing global variables to the configuration
    3. Set the configuration as the global configuration
    4. Return the configuration object
    
    Args:
        processing_dir: Processing directory path
        preset: Preset name to use as base
        
    Returns:
        ProcessingConfig: The migrated configuration
    """
    # Convert processing_dir to Path if it's a string
    if isinstance(processing_dir, str):
        processing_dir = Path(processing_dir)
    
    # Import sms module for migration
    import sms
    
    # Migrate the module to configuration
    config, updates = migrate_module_to_configuration(sms, processing_dir, preset)
    
    logger.info(f"✅ SMS module migrated to configuration with {len(updates)} updates")
    return config


def get_effective_processing_config() -> Optional[ProcessingConfig]:
    """
    Get the effective processing configuration.
    
    Returns:
        ProcessingConfig: The current configuration, or None if not set
    """
    try:
        manager = get_configuration_manager()
        return manager.get_current_config()
    except Exception as e:
        logger.warning(f"Failed to get effective processing config: {e}")
        return None


def validate_processing_config(config: ProcessingConfig) -> bool:
    """
    Validate a processing configuration.
    
    Args:
        config: ProcessingConfig to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Basic validation
        if not config.processing_dir.exists():
            logger.error(f"Processing directory does not exist: {config.processing_dir}")
            return False
        
        if not config.processing_dir.is_dir():
            logger.error(f"Processing path is not a directory: {config.processing_dir}")
            return False
        
        # Check for expected subdirectories
        calls_dir = config.processing_dir / "Calls"
        if not calls_dir.exists():
            logger.warning(f"Calls directory not found: {calls_dir}")
            logger.warning("This may cause attachment processing to fail")
        
        # Check for HTML files
        html_files = list(config.processing_dir.rglob("*.html"))
        if not html_files:
            logger.warning(f"No HTML files found in processing directory: {config.processing_dir}")
            logger.warning("This may indicate the wrong directory was specified")
        
        # Validate output directory can be created
        try:
            output_dir = config.output_dir
            output_dir.mkdir(exist_ok=True)
            
            # Test write permissions
            test_file = output_dir / ".test_write_permission"
            test_file.write_text("test")
            test_file.unlink()
            logger.info("✅ Write permissions verified for output directory")
        except Exception as e:
            logger.error(f"❌ Cannot create or write to output directory: {e}")
            return False
        
        logger.info("✅ Processing configuration validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Processing configuration validation failed: {e}")
        return False


def create_processing_config_from_legacy(
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
    Create a ProcessingConfig from legacy parameters.
    
    This function provides a bridge between the old parameter-based approach
    and the new configuration object approach.
    
    Args:
        processing_dir: Path to the processing directory
        enable_phone_prompts: Whether to enable phone number alias prompts
        buffer_size: Buffer size for file I/O operations
        batch_size: Batch size for processing files
        cache_size: Cache size for performance optimization
        large_dataset: Whether this is a large dataset
        output_format: Output format ('xml' or 'html')
        preset: Preset name to use as base
        
    Returns:
        ProcessingConfig: Configuration object with the specified settings
    """
    # Convert processing_dir to Path if it's a string
    if isinstance(processing_dir, str):
        processing_dir = Path(processing_dir)
    
    # Start with preset configuration
    from .processing_config import ConfigurationBuilder
    config = ConfigurationBuilder.create_with_presets(processing_dir, preset)
    
    # Override with legacy parameters
    config_dict = config.to_dict()
    config_dict.update({
        'enable_phone_prompts': enable_phone_prompts,
        'buffer_size': buffer_size,
        'batch_size': batch_size,
        'cache_size': cache_size,
        'large_dataset': large_dataset,
        'output_format': output_format,
    })
    
    # Create new configuration with overrides
    final_config = ProcessingConfig.from_dict(config_dict)
    
    logger.info(f"✅ ProcessingConfig created from legacy parameters with {preset} preset")
    return final_config
