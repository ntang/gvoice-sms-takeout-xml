"""
SMS Module Patch for Configuration System Integration.

This module provides patches and modifications to integrate the existing sms.py
module with the new configuration system.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .processing_config import ProcessingConfig
from .configuration_manager import get_configuration_manager, set_global_configuration
from .function_signatures import setup_processing_paths_with_config
# from .backward_compatibility import enable_backward_compatibility  # Removed - migration complete

logger = logging.getLogger(__name__)


class SMSModulePatcher:
    """
    Patches the sms.py module to integrate with the new configuration system.
    
    This class provides methods to:
    1. Patch global variables to use configuration values
    2. Replace function calls with configuration-driven versions
    3. Integrate with new configuration system
    4. Enable gradual migration
    """
    
    def __init__(self):
        """Initialize the SMS module patcher."""
        self._patched_functions = set()
        self._patched_globals = set()
        self._original_values = {}
        
        logger.info("SMS Module Patcher initialized")
    
    def patch_global_variables(self, config: ProcessingConfig) -> None:
        """
        Patch global variables in sms.py to use configuration values.
        
        Args:
            config: ProcessingConfig object containing the values to use
        """
        try:
            import sms
        except ImportError:
            # For testing, create a mock module
            from unittest.mock import MagicMock
            sms = MagicMock()
        
        logger.info("🔧 Patching global variables in sms.py...")
        
        # Store original values for potential restoration
        self._store_original_values(sms)
        
        # Patch processing directory variables
        if hasattr(sms, 'PROCESSING_DIRECTORY'):
            sms.PROCESSING_DIRECTORY = config.processing_dir
            self._patched_globals.add('PROCESSING_DIRECTORY')
            logger.debug(f"Patched PROCESSING_DIRECTORY: {config.processing_dir}")
        
        if hasattr(sms, 'OUTPUT_DIRECTORY'):
            sms.OUTPUT_DIRECTORY = config.output_dir
            self._patched_globals.add('OUTPUT_DIRECTORY')
            logger.debug(f"Patched OUTPUT_DIRECTORY: {config.output_dir}")
        
        # Patch performance variables
        # Performance settings are now hardcoded in shared_constants.py for optimal defaults
        
        # Patch validation flags
        if hasattr(sms, 'ENABLE_PATH_VALIDATION'):
            sms.ENABLE_PATH_VALIDATION = config.enable_path_validation
            self._patched_globals.add('ENABLE_PATH_VALIDATION')
            logger.debug(f"Patched ENABLE_PATH_VALIDATION: {config.enable_path_validation}")
        
        if hasattr(sms, 'ENABLE_RUNTIME_VALIDATION'):
            sms.ENABLE_RUNTIME_VALIDATION = config.enable_runtime_validation
            self._patched_globals.add('ENABLE_RUNTIME_VALIDATION')
            logger.debug(f"Patched ENABLE_RUNTIME_VALIDATION: {config.enable_runtime_validation}")
        
        # Patch test mode variables
        if hasattr(sms, 'TEST_MODE'):
            sms.TEST_MODE = config.test_mode
            self._patched_globals.add('TEST_MODE')
            logger.debug(f"Patched TEST_MODE: {config.test_mode}")
        
        if hasattr(sms, 'TEST_LIMIT'):
            sms.TEST_LIMIT = config.test_limit
            self._patched_globals.add('TEST_LIMIT')
            logger.debug(f"Patched TEST_LIMIT: {config.test_limit}")
        
        # Patch phone prompts setting
        if hasattr(sms, 'ENABLE_PHONE_PROMPTS'):
            sms.ENABLE_PHONE_PROMPTS = config.enable_phone_prompts
            self._patched_globals.add('ENABLE_PHONE_PROMPTS')
            logger.debug(f"Patched ENABLE_PHONE_PROMPTS: {config.enable_phone_prompts}")
        
        # Patch output format
        if hasattr(sms, 'OUTPUT_FORMAT'):
            sms.OUTPUT_FORMAT = config.output_format
            self._patched_globals.add('OUTPUT_FORMAT')
            logger.debug(f"Patched OUTPUT_FORMAT: {config.output_format}")
        
        # Patch large dataset flag
        if hasattr(sms, 'LARGE_DATASET'):
            sms.LARGE_DATASET = config.large_dataset
            self._patched_globals.add('LARGE_DATASET')
            logger.debug(f"Patched LARGE_DATASET: {config.large_dataset}")
        
        # Patch date filtering variables
        if hasattr(sms, 'DATE_FILTER_OLDER_THAN'):
            sms.DATE_FILTER_OLDER_THAN = config.exclude_older_than
            self._patched_globals.add('DATE_FILTER_OLDER_THAN')
            logger.debug(f"Patched DATE_FILTER_OLDER_THAN: {config.exclude_older_than}")
        
        if hasattr(sms, 'DATE_FILTER_NEWER_THAN'):
            sms.DATE_FILTER_NEWER_THAN = config.exclude_newer_than
            self._patched_globals.add('DATE_FILTER_NEWER_THAN')
            logger.debug(f"Patched DATE_FILTER_NEWER_THAN: {config.exclude_newer_than}")
        
        # Patch phone filtering variables
        if hasattr(sms, 'FILTER_NUMBERS_WITHOUT_ALIASES'):
            sms.FILTER_NUMBERS_WITHOUT_ALIASES = config.filter_numbers_without_aliases
            self._patched_globals.add('FILTER_NUMBERS_WITHOUT_ALIASES')
            logger.debug(f"Patched FILTER_NUMBERS_WITHOUT_ALIASES: {config.filter_numbers_without_aliases}")
        
        if hasattr(sms, 'FILTER_NON_PHONE_NUMBERS'):
            sms.FILTER_NON_PHONE_NUMBERS = config.filter_non_phone_numbers
            self._patched_globals.add('FILTER_NON_PHONE_NUMBERS')
            logger.debug(f"Patched FILTER_NON_PHONE_NUMBERS: {config.filter_non_phone_numbers}")
        
        if hasattr(sms, 'SKIP_FILTERED_CONTACTS'):
            sms.SKIP_FILTERED_CONTACTS = config.skip_filtered_contacts
            self._patched_globals.add('SKIP_FILTERED_CONTACTS')
            logger.debug(f"Patched SKIP_FILTERED_CONTACTS: {config.skip_filtered_contacts}")
        
        if hasattr(sms, 'INCLUDE_SERVICE_CODES'):
            sms.INCLUDE_SERVICE_CODES = config.include_service_codes
            self._patched_globals.add('INCLUDE_SERVICE_CODES')
            logger.debug(f"Patched INCLUDE_SERVICE_CODES: {config.include_service_codes}")
        
        if hasattr(sms, 'FILTER_GROUPS_WITH_ALL_FILTERED'):
            sms.FILTER_GROUPS_WITH_ALL_FILTERED = config.filter_groups_with_all_filtered
            self._patched_globals.add('FILTER_GROUPS_WITH_ALL_FILTERED')
            logger.debug(f"Patched FILTER_GROUPS_WITH_ALL_FILTERED: {config.filter_groups_with_all_filtered}")
        
        if hasattr(sms, 'FULL_RUN'):
            sms.FULL_RUN = config.full_run
            self._patched_globals.add('FULL_RUN')
            logger.debug(f"Patched FULL_RUN: {config.full_run}")
        
        # Also update shared_constants module to ensure consistency
        try:
            from core import shared_constants
            
            # Update date filtering variables in shared_constants
            shared_constants.DATE_FILTER_OLDER_THAN = config.exclude_older_than
            shared_constants.DATE_FILTER_NEWER_THAN = config.exclude_newer_than
            
            # Update phone filtering variables in shared_constants
            shared_constants.FILTER_NUMBERS_WITHOUT_ALIASES = config.filter_numbers_without_aliases
            shared_constants.FILTER_NON_PHONE_NUMBERS = config.filter_non_phone_numbers
            shared_constants.SKIP_FILTERED_CONTACTS = config.skip_filtered_contacts
            shared_constants.INCLUDE_SERVICE_CODES = config.include_service_codes
            shared_constants.FILTER_GROUPS_WITH_ALL_FILTERED = config.filter_groups_with_all_filtered
            shared_constants.FULL_RUN = config.full_run
            
            logger.debug("✅ Updated shared_constants module with filtering configuration")
            
        except ImportError as e:
            logger.warning(f"Could not update shared_constants module: {e}")
        
        logger.info(f"✅ Patched {len(self._patched_globals)} global variables")
    
    def patch_functions(self) -> None:
        """
        Patch functions in sms.py to use the new configuration system.
        
        This replaces key functions with configuration-driven versions
        for the new configuration system.
        """
        try:
            import sms
        except ImportError:
            # For testing, create a mock module
            from unittest.mock import MagicMock
            sms = MagicMock()
        
        logger.info("🔧 Patching functions in sms.py...")
        
        # Store original functions for potential restoration
        self._store_original_functions(sms)
        
        # Patch setup_processing_paths to use configuration
        if hasattr(sms, 'setup_processing_paths'):
            # Create a wrapper that maintains the original signature
            def patched_setup_processing_paths(
                processing_dir: Union[str, Path],
                enable_phone_prompts: bool = False,
                buffer_size: int = 8192,
                batch_size: int = 1000,
                cache_size: int = 25000,
                large_dataset: bool = False,
                phone_lookup_file: Optional[Path] = None,
            ) -> None:
                """Patched version of setup_processing_paths that uses configuration."""
                # Get the current configuration
                manager = get_configuration_manager()
                current_config = manager.get_current_config()
                
                if current_config:
                    # Use the current configuration
                    logger.info("🔄 Using current configuration for setup_processing_paths")
                    setup_processing_paths_with_config(current_config)
                else:
                    # Fall back to original behavior
                    logger.warning("⚠️  No configuration available, falling back to original setup_processing_paths")
                    # Call the original function (stored in _original_values)
                    original_func = self._original_values.get('setup_processing_paths')
                    if original_func:
                        original_func(
                            processing_dir, enable_phone_prompts, large_dataset, phone_lookup_file
                        )
                    else:
                        logger.error("❌ Original function not available")
                        raise RuntimeError("Original setup_processing_paths function not available")
            
            # Replace the function
            patched_setup_processing_paths._is_patched = True
            sms.setup_processing_paths = patched_setup_processing_paths
            self._patched_functions.add('setup_processing_paths')
            logger.debug("Patched setup_processing_paths function")
        
        # Patch validate_processing_directory to use configuration
        if hasattr(sms, 'validate_processing_directory'):
            from .function_signatures import validate_processing_config
            
            def patched_validate_processing_directory(processing_dir: Union[str, Path]) -> bool:
                """Patched version of validate_processing_directory that uses configuration."""
                # Convert to Path if needed
                if isinstance(processing_dir, str):
                    processing_dir = Path(processing_dir)
                
                # Create a minimal configuration for validation
                from .processing_config import ProcessingConfig
                config = ProcessingConfig(processing_dir=processing_dir)
                
                # Use the new validation function
                return validate_processing_config(config)
            
            # Replace the function
            sms.validate_processing_directory = patched_validate_processing_directory
            self._patched_functions.add('validate_processing_directory')
            logger.debug("Patched validate_processing_directory function")
        
        logger.info(f"✅ Patched {len(self._patched_functions)} functions")
    
    def _store_original_values(self, sms_module) -> None:
        """Store original values of global variables for potential restoration."""
        for attr_name in dir(sms_module):
            if attr_name.isupper() and not attr_name.startswith('_'):
                try:
                    value = getattr(sms_module, attr_name)
                    self._original_values[attr_name] = value
                except Exception as e:
                    logger.debug(f"Could not store original value for {attr_name}: {e}")
    
    def _store_original_functions(self, sms_module) -> None:
        """Store original functions for potential restoration."""
        function_names = ['setup_processing_paths', 'validate_processing_directory']
        
        for func_name in function_names:
            if hasattr(sms_module, func_name):
                func = getattr(sms_module, func_name)
                if callable(func):
                    self._original_values[func_name] = func
                    logger.debug(f"Stored original function: {func_name}")
    
    def restore_original_values(self) -> None:
        """Restore original values of patched global variables."""
        if not self._patched_globals:
            logger.info("No patched globals to restore")
            return
        
        try:
            import sms
        except ImportError:
            # For testing, create a mock module
            from unittest.mock import MagicMock
            sms = MagicMock()
        
        logger.info("🔄 Restoring original global variable values...")
        
        for global_name in self._patched_globals:
            if global_name in self._original_values:
                original_value = self._original_values[global_name]
                setattr(sms, global_name, original_value)
                logger.debug(f"Restored {global_name}: {original_value}")
        
        self._patched_globals.clear()
        logger.info("✅ Restored original global variable values")
    
    def restore_original_functions(self) -> None:
        """Restore original functions."""
        if not self._patched_functions:
            logger.info("No patched functions to restore")
            return
        
        try:
            import sms
        except ImportError:
            # For testing, create a mock module
            from unittest.mock import MagicMock
            sms = MagicMock()
        
        logger.info("🔄 Restoring original functions...")
        
        for func_name in self._patched_functions:
            if func_name in self._original_values:
                original_func = self._original_values[func_name]
                setattr(sms, func_name, original_func)
                logger.debug(f"Restored function: {func_name}")
        
        self._patched_functions.clear()
        logger.info("✅ Restored original functions")
    
    def get_patch_status(self) -> Dict[str, Any]:
        """
        Get the current patch status.
        
        Returns:
            Dict containing patch status information
        """
        return {
            'patched_globals': list(self._patched_globals),
            'patched_functions': list(self._patched_functions),
            'total_patched': len(self._patched_globals) + len(self._patched_functions),
            'has_original_values': bool(self._original_values)
        }


def patch_sms_module(config: ProcessingConfig) -> SMSModulePatcher:
    """
    Patch the sms.py module to use the new configuration system.
    
    Args:
        config: ProcessingConfig object to use for patching
        
    Returns:
        SMSModulePatcher instance for managing the patches
    """
    logger.info("🔧 Starting SMS module patching process...")
    
    # Create patcher instance
    patcher = SMSModulePatcher()
    
    # Patch global variables
    patcher.patch_global_variables(config)
    
    # Patch functions
    patcher.patch_functions()
    
    # Backward compatibility removed - migration complete
    # enable_backward_compatibility()
    
    # Register the patcher
    register_patcher(patcher)
    
    logger.info("✅ SMS module patching completed successfully")
    return patcher


def unpatch_sms_module(patcher: SMSModulePatcher) -> None:
    """
    Remove patches from the sms.py module.
    
    Args:
        patcher: SMSModulePatcher instance to use for unpatching
    """
    logger.info("🔄 Removing SMS module patches...")
    
    # Restore original values and functions
    patcher.restore_original_values()
    patcher.restore_original_functions()
    
    # Unregister the patcher
    unregister_patcher(patcher)
    
    logger.info("✅ SMS module patches removed successfully")


def get_sms_module_patcher() -> SMSModulePatcher:
    """
    Get a new SMS module patcher instance.
    
    Returns:
        SMSModulePatcher instance
    """
    return SMSModulePatcher()


def is_sms_module_patched() -> bool:
    """
    Check if the SMS module has been patched.
    
    Returns:
        True if patched, False otherwise
    """
    # Primary check: active patchers list (most reliable)
    if len(_active_patchers) > 0:
        return True
    
    # Secondary check: if no active patchers, we're not patched
    return False


# Convenience functions for common operations
def quick_patch_sms_module(processing_dir: Union[str, Path], **kwargs) -> SMSModulePatcher:
    """
    Quick patch the SMS module with basic configuration.
    
    Args:
        processing_dir: Processing directory path
        **kwargs: Additional configuration options
        
    Returns:
        SMSModulePatcher instance
    """
    from .processing_config import ConfigurationBuilder
    
    # Convert string to Path if needed
    if isinstance(processing_dir, str):
        processing_dir = Path(processing_dir)
    
    # Create configuration from processing directory and kwargs
    config = ConfigurationBuilder.create_with_presets(processing_dir, "default")
    
    # Override with kwargs if provided
    if kwargs:
        config_dict = config.to_dict()
        config_dict.update(kwargs)
        config = config.__class__(**config_dict)
    
    # Patch the module
    return patch_sms_module(config)


def quick_unpatch_sms_module() -> None:
    """Quick unpatch the SMS module if it's been patched."""
    if is_sms_module_patched():
        logger.warning("⚠️  SMS module appears to be patched but no patcher instance available")
        logger.warning("Manual restoration may be required")
    else:
        logger.info("ℹ️  SMS module is not patched")


# Global registry for active patchers (for testing and tracking)
_active_patchers = []


def get_active_patchers() -> List['SMSModulePatcher']:
    """Get list of active patchers (for testing and debugging)."""
    return _active_patchers.copy()


def get_active_patcher_count() -> int:
    """Get the number of active patchers."""
    return len(_active_patchers)


def register_patcher(patcher: 'SMSModulePatcher') -> None:
    """Register an active patcher."""
    _active_patchers.append(patcher)


def unregister_patcher(patcher: 'SMSModulePatcher') -> None:
    """Unregister an active patcher."""
    if patcher in _active_patchers:
        _active_patchers.remove(patcher)
