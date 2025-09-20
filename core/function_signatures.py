"""
Function Signature Updates for SMS/MMS processing system.

This module provides updated function signatures that accept ProcessingConfig
objects for the new architecture.
"""

import logging
from pathlib import Path
from typing import Optional, Union

from .processing_config import ProcessingConfig
from .configuration_manager import get_configuration_manager, set_global_configuration
from .shared_constants import BUFFER_SIZE_OPTIMAL, BATCH_SIZE_OPTIMAL
from .configuration_migration import migrate_module_to_configuration

logger = logging.getLogger(__name__)


def setup_processing_paths_with_config(
    config: ProcessingConfig,
    enable_phone_prompts: Optional[bool] = None,
    buffer_size: Optional[int] = None,
    batch_size: Optional[int] = None,
    cache_size: Optional[int] = None,
    large_dataset: Optional[bool] = None,
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
        
    Raises:
        ValueError: If parameters are invalid
        TypeError: If parameter types are incorrect
    """
    # Set global configuration for other parts of the system
    set_global_configuration(config)
    
    # Use override values if provided, otherwise use config values
    effective_phone_prompts = enable_phone_prompts if enable_phone_prompts is not None else config.enable_phone_prompts
    effective_buffer_size = buffer_size if buffer_size is not None else BUFFER_SIZE_OPTIMAL
    effective_batch_size = batch_size if batch_size is not None else BATCH_SIZE_OPTIMAL
    effective_cache_size = cache_size if cache_size is not None else 25000  # Default cache size
    effective_large_dataset = large_dataset if large_dataset is not None else config.large_dataset
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
        phone_lookup_file=effective_phone_lookup_file,
    )
    
    logger.info("✅ Processing paths initialized with configuration object")


# Legacy functions removed - migration complete


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


# Legacy config creation removed - use ConfigurationBuilder directly
