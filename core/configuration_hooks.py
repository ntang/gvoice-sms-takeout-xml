"""
Configuration Validation Hooks for SMS/MMS processing system.

Provides hooks and utilities for integrating the new configuration
system with existing validation and processing logic.
"""

import logging
import functools
from typing import Any, Callable, Dict, Optional, Union
from pathlib import Path

from .configuration_manager import get_configuration_manager, get_global_configuration
from .processing_config import ProcessingConfig

logger = logging.getLogger(__name__)


def with_configuration_validation(func: Callable) -> Callable:
    """
    Decorator that validates configuration before function execution.
    
    This decorator ensures that the configuration is valid and up-to-date
    before executing the decorated function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        manager = get_configuration_manager()
        
        # Refresh configuration if needed
        if not manager.refresh_configuration():
            logger.warning("Configuration validation failed, using fallback")
        
        # Execute the function
        return func(*args, **kwargs)
    
    return wrapper


def require_configuration(func: Callable) -> Callable:
    """
    Decorator that requires a valid configuration to be present.
    
    This decorator ensures that a configuration exists before executing
    the decorated function, raising an error if none is available.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            config = get_global_configuration()
            if not config:
                raise RuntimeError("No configuration available")
        except Exception as e:
            logger.error(f"Configuration required but not available: {e}")
            raise RuntimeError(f"Configuration required: {e}")
        
        return func(*args, **kwargs)
    
    return wrapper


def configuration_driven(
    config_key: str,
    default_value: Any = None,
    validation_func: Optional[Callable] = None
) -> Callable:
    """
    Decorator that makes a function's behavior driven by configuration.
    
    Args:
        config_key: Configuration key to check
        default_value: Default value if configuration key not found
        validation_func: Optional validation function for the configuration value
        
    Returns:
        Decorated function that checks configuration before execution
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                config = get_global_configuration()
                config_value = getattr(config, config_key, default_value)
                
                # Validate the configuration value if validation function provided
                if validation_func and not validation_func(config_value):
                    logger.warning(f"Configuration validation failed for {config_key}: {config_value}")
                    config_value = default_value
                
                # Add configuration value to kwargs for the function to use
                kwargs[f'config_{config_key}'] = config_value
                
            except Exception as e:
                logger.warning(f"Failed to get configuration for {config_key}: {e}")
                config_value = default_value
                kwargs[f'config_{config_key}'] = config_value
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class ConfigurationValidator:
    """Configuration validation utilities."""
    
    @staticmethod
    def validate_phone_prompts_enabled(value: bool) -> bool:
        """Validate that phone prompts setting is reasonable."""
        return isinstance(value, bool)
    
    @staticmethod
    def validate_test_mode(value: bool) -> bool:
        """Validate that test mode setting is reasonable."""
        return isinstance(value, bool)
    
    @staticmethod
    def validate_output_format(value: str) -> bool:
        """Validate output format setting."""
        return value in ["html", "xml"]
    
    @staticmethod
    def validate_max_workers(value: int) -> bool:
        """Validate max workers setting."""
        return isinstance(value, int) and 1 <= value <= 64
    
    @staticmethod
    def validate_chunk_size(value: int) -> bool:
        """Validate chunk size setting."""
        return isinstance(value, int) and 1 <= value <= 10000
    
    @staticmethod
    def validate_buffer_size(value: int) -> bool:
        """Validate buffer size setting."""
        return isinstance(value, int) and 1024 <= value <= 1048576  # 1KB to 1MB
    
    @staticmethod
    def validate_processing_directory(value: Path) -> bool:
        """Validate processing directory path."""
        return isinstance(value, Path) and value.exists() and value.is_dir()
    
    @staticmethod
    def validate_output_directory(value: Path) -> bool:
        """Validate output directory path."""
        return isinstance(value, Path) and value.parent.exists()


class ConfigurationIntegrator:
    """Utilities for integrating configuration with existing code."""
    
    @staticmethod
    def get_phone_prompts_setting() -> bool:
        """Get phone prompts setting from configuration."""
        try:
            config = get_global_configuration()
            return config.should_enable_phone_prompts()
        except Exception as e:
            logger.warning(f"Failed to get phone prompts setting: {e}")
            return False
    
    @staticmethod
    def get_test_mode_setting() -> bool:
        """Get test mode setting from configuration."""
        try:
            config = get_global_configuration()
            return config.is_test_mode()
        except Exception as e:
            logger.warning(f"Failed to get test mode setting: {e}")
            return False
    
    @staticmethod
    def get_test_limit_setting() -> int:
        """Get test limit setting from configuration."""
        try:
            config = get_global_configuration()
            return config.get_test_limit()
        except Exception as e:
            logger.warning(f"Failed to get test limit setting: {e}")
            return 100
    
    @staticmethod
    def get_output_format_setting() -> str:
        """Get output format setting from configuration."""
        try:
            config = get_global_configuration()
            return config.get_output_format()
        except Exception as e:
            logger.warning(f"Failed to get output format setting: {e}")
            return "html"
    
    @staticmethod
    def get_processing_directory_setting() -> Optional[Path]:
        """Get processing directory setting from configuration."""
        try:
            config = get_global_configuration()
            return config.get_processing_directory()
        except Exception as e:
            logger.warning(f"Failed to get processing directory setting: {e}")
            return None
    
    @staticmethod
    def get_output_directory_setting() -> Optional[Path]:
        """Get output directory setting from configuration."""
        try:
            config = get_global_configuration()
            return config.get_output_directory()
        except Exception as e:
            logger.warning(f"Failed to get output directory setting: {e}")
            return None
    
    @staticmethod
    def get_performance_settings() -> Dict[str, Any]:
        """Get performance-related settings from configuration."""
        try:
            config = get_global_configuration()
            return {
                'max_workers': config.max_workers,
                'chunk_size': config.chunk_size,
                'batch_size': config.batch_size,
                'buffer_size': config.buffer_size,
                'cache_size': config.cache_size,
                'memory_threshold': config.memory_threshold,
                'enable_parallel_processing': config.enable_parallel_processing,
                'enable_streaming_parsing': config.enable_streaming_parsing,
                'enable_mmap_for_large_files': config.enable_mmap_for_large_files,
            }
        except Exception as e:
            logger.warning(f"Failed to get performance settings: {e}")
            return {}
    
    @staticmethod
    def get_validation_settings() -> Dict[str, Any]:
        """Get validation-related settings from configuration."""
        try:
            config = get_global_configuration()
            return {
                'enable_path_validation': config.enable_path_validation,
                'enable_runtime_validation': config.enable_runtime_validation,
                'strict_mode': config.strict_mode,
            }
        except Exception as e:
            logger.warning(f"Failed to get validation settings: {e}")
            return {}
    
    @staticmethod
    def get_debug_settings() -> Dict[str, Any]:
        """Get debug-related settings from configuration."""
        try:
            config = get_global_configuration()
            return {
                'log_level': config.log_level,
                'verbose': config.verbose,
                'debug': config.debug,
                'debug_attachments': config.debug_attachments,
                'debug_paths': config.debug_paths,
            }
        except Exception as e:
            logger.warning(f"Failed to get debug settings: {e}")
            return {}


def get_configuration_integrator() -> ConfigurationIntegrator:
    """Get the global configuration integrator instance."""
    return ConfigurationIntegrator()


def get_configuration_validator() -> ConfigurationValidator:
    """Get the global configuration validator instance."""
    return ConfigurationValidator()


# Convenience functions for common configuration access patterns
def is_phone_prompts_enabled() -> bool:
    """Check if phone prompts are enabled."""
    return ConfigurationIntegrator.get_phone_prompts_setting()


def is_test_mode_enabled() -> bool:
    """Check if test mode is enabled."""
    return ConfigurationIntegrator.get_test_mode_setting()


def get_test_limit() -> int:
    """Get the test limit."""
    return ConfigurationIntegrator.get_test_limit_setting()


def get_output_format() -> str:
    """Get the output format."""
    return ConfigurationIntegrator.get_output_format_setting()


def get_processing_directory() -> Optional[Path]:
    """Get the processing directory."""
    return ConfigurationIntegrator.get_processing_directory_setting()


def get_output_directory() -> Optional[Path]:
    """Get the output directory."""
    return ConfigurationIntegrator.get_output_directory_setting()
