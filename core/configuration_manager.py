"""
Configuration Manager for SMS/MMS processing system.

Provides runtime configuration access, caching, and integration
with the existing codebase during the transition to the new
configuration system.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from .processing_config import ProcessingConfig, ConfigurationBuilder

logger = logging.getLogger(__name__)


@dataclass
class ConfigurationCache:
    """Configuration cache entry with metadata."""
    config: ProcessingConfig
    timestamp: float
    source: str
    version: str = "1.0"


class ConfigurationManager:
    """
    Manages runtime configuration access and caching.
    
    This class provides a bridge between the new configuration system
    and the existing codebase, allowing gradual migration while
    maintaining backward compatibility.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._config_cache: Dict[str, ConfigurationCache] = {}
        self._default_config: Optional[ProcessingConfig] = None
        self._current_config: Optional[ProcessingConfig] = None
        self._lock = threading.RLock()
        self._cache_ttl = 300  # 5 minutes default TTL
        self._last_validation = 0
        self._validation_interval = 60  # 1 minute validation interval
        
        # Configuration source tracking
        self._config_sources = {
            'cli': None,
            'environment': None,
            'preset': None,
            'merged': None
        }
        
        logger.info("Configuration Manager initialized")
    
    def set_default_config(self, config: Optional[ProcessingConfig]) -> None:
        """Set the default configuration for fallback."""
        with self._lock:
            self._default_config = config
            if config:
                logger.debug(f"Default configuration set: {config.processing_dir}")
            else:
                logger.debug("Default configuration cleared")
    
    def get_default_config(self) -> Optional[ProcessingConfig]:
        """Get the default configuration."""
        return self._default_config
    
    def set_current_config(self, config: Optional[ProcessingConfig]) -> None:
        """Set the current active configuration."""
        with self._lock:
            self._current_config = config
            if config:
                logger.debug(f"Current configuration set: {config.processing_dir}")
            else:
                logger.debug("Current configuration cleared")
    
    def get_current_config(self) -> Optional[ProcessingConfig]:
        """Get the current active configuration."""
        return self._current_config
    
    def get_effective_config(self) -> ProcessingConfig:
        """
        Get the effective configuration, falling back to default if needed.
        
        Returns:
            ProcessingConfig: The effective configuration to use
        """
        if self._current_config:
            return self._current_config
        elif self._default_config:
            logger.warning("Using default configuration as fallback")
            return self._default_config
        else:
            raise RuntimeError("No configuration available")
    
    def build_config_from_cli(self, cli_args: Dict[str, Any]) -> ProcessingConfig:
        """
        Build configuration from CLI arguments and cache it.
        
        Args:
            cli_args: Dictionary of CLI argument values
            
        Returns:
            ProcessingConfig: Built configuration
        """
        cache_key = f"cli_{hash(str(sorted(cli_args.items())))}"
        
        # Check cache first
        cached = self._get_cached_config(cache_key)
        if cached:
            return cached
        
        try:
            config = ConfigurationBuilder.from_cli_args(cli_args)
            self._cache_config(cache_key, config, "cli")
            self._config_sources['cli'] = config
            logger.debug(f"Built CLI configuration: {config.processing_dir}")
            return config
        except Exception as e:
            logger.error(f"Failed to build CLI configuration: {e}")
            raise
    
    def build_config_from_environment(self) -> ProcessingConfig:
        """
        Build configuration from environment variables and cache it.
        
        Returns:
            ProcessingConfig: Built configuration
        """
        cache_key = "environment"
        
        # Check cache first
        cached = self._get_cached_config(cache_key)
        if cached:
            return cached
        
        try:
            config = ConfigurationBuilder.from_environment()
            self._cache_config(cache_key, config, "environment")
            self._config_sources['environment'] = config
            logger.debug(f"Built environment configuration: {config.processing_dir}")
            return config
        except Exception as e:
            logger.error(f"Failed to build environment configuration: {e}")
            raise
    
    def build_config_from_preset(self, processing_dir: Path, preset: str = "default") -> ProcessingConfig:
        """
        Build configuration from preset and cache it.
        
        Args:
            processing_dir: Processing directory path
            preset: Preset name ('default', 'test', 'production')
            
        Returns:
            ProcessingConfig: Built configuration
        """
        cache_key = f"preset_{preset}_{processing_dir}"
        
        # Check cache first
        cached = self._get_cached_config(cache_key)
        if cached:
            return cached
        
        try:
            config = ConfigurationBuilder.create_with_presets(processing_dir, preset)
            self._cache_config(cache_key, config, "preset")
            self._config_sources['preset'] = config
            logger.debug(f"Built preset configuration: {preset} -> {config.processing_dir}")
            return config
        except Exception as e:
            logger.error(f"Failed to build preset configuration: {e}")
            raise
    
    def merge_configurations(self, *configs: ProcessingConfig) -> ProcessingConfig:
        """
        Merge multiple configurations and cache the result.
        
        Args:
            *configs: ProcessingConfig instances to merge
            
        Returns:
            ProcessingConfig: Merged configuration
        """
        if not configs:
            raise ValueError("At least one configuration must be provided")
        
        if len(configs) == 1:
            return configs[0]
        
        # Create cache key from config hashes
        config_hashes = [hash(str(config.to_dict())) for config in configs]
        cache_key = f"merged_{'_'.join(map(str, config_hashes))}"
        
        # Check cache first
        cached = self._get_cached_config(cache_key)
        if cached:
            return cached
        
        try:
            merged_config = ConfigurationBuilder.merge_configs(*configs)
            self._cache_config(cache_key, merged_config, "merged")
            self._config_sources['merged'] = merged_config
            logger.debug(f"Merged {len(configs)} configurations")
            return merged_config
        except Exception as e:
            logger.error(f"Failed to merge configurations: {e}")
            raise
    
    def build_complete_configuration(
        self,
        processing_dir: Union[str, Path],
        cli_args: Optional[Dict[str, Any]] = None,
        preset: str = "default",
        use_environment: bool = True
    ) -> ProcessingConfig:
        """
        Build complete configuration from all available sources.
        
        Args:
            processing_dir: Processing directory path
            cli_args: Optional CLI arguments
            preset: Preset name to use
            use_environment: Whether to include environment variables
            
        Returns:
            ProcessingConfig: Complete merged configuration
        """
        # Convert processing_dir to Path if it's a string
        if isinstance(processing_dir, str):
            processing_dir = Path(processing_dir)
        
        configs = []
        
        # Start with preset configuration
        preset_config = self.build_config_from_preset(processing_dir, preset)
        configs.append(preset_config)
        
        # Add environment configuration if requested
        if use_environment:
            try:
                env_config = self.build_config_from_environment()
                configs.append(env_config)
            except Exception as e:
                logger.warning(f"Environment configuration unavailable: {e}")
        
        # Add CLI configuration if provided
        if cli_args:
            try:
                cli_config = self.build_config_from_cli(cli_args)
                configs.append(cli_config)
            except Exception as e:
                logger.warning(f"CLI configuration unavailable: {e}")
        
        # Merge all configurations
        final_config = self.merge_configurations(*configs)
        
        # Set as current configuration
        self.set_current_config(final_config)
        
        logger.info(f"Complete configuration built: {final_config.processing_dir}")
        return final_config
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from the current configuration.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = self.get_effective_config()
        return getattr(config, key, default)
    
    def get_active_patchers(self) -> List['SMSModulePatcher']:
        """
        Get list of active SMS module patchers.
        
        This method provides access to the patcher registry for testing
        and debugging purposes.
        
        Returns:
            List of active SMSModulePatcher instances
        """
        try:
            from .sms_patch import get_active_patchers
            return get_active_patchers()
        except ImportError:
            logger.warning("SMS patch module not available")
            return []
    
    def get_phone_prompts_enabled(self) -> bool:
        """Get whether phone prompts are enabled."""
        config = self.get_effective_config()
        return config.should_enable_phone_prompts()
    
    def get_test_mode(self) -> bool:
        """Get whether test mode is enabled."""
        config = self.get_effective_config()
        return config.is_test_mode()
    
    def get_test_limit(self) -> int:
        """Get the test limit."""
        config = self.get_effective_config()
        return config.get_test_limit()
    
    def get_output_format(self) -> str:
        """Get the output format."""
        config = self.get_effective_config()
        return config.get_output_format()
    
    def get_processing_directory(self) -> Path:
        """Get the processing directory."""
        config = self.get_effective_config()
        return config.get_processing_directory()
    
    def get_output_directory(self) -> Path:
        """Get the output directory."""
        config = self.get_effective_config()
        return config.get_output_directory()
    
    def validate_configuration(self, config: ProcessingConfig) -> bool:
        """
        Validate a configuration object.
        
        Args:
            config: Configuration to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # The ProcessingConfig constructor already validates
            # This is just a runtime check
            _ = config.processing_dir
            _ = config.output_dir
            # Note: max_workers was removed from ProcessingConfig and moved to shared_constants
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def refresh_configuration(self) -> bool:
        """
        Refresh the current configuration from sources.
        
        Returns:
            bool: True if refresh successful, False otherwise
        """
        current_time = time.time()
        
        # Check if we need to refresh
        if current_time - self._last_validation < self._validation_interval:
            return True
        
        try:
            if self._current_config:
                # Re-validate current configuration
                if self.validate_configuration(self._current_config):
                    self._last_validation = current_time
                    return True
                else:
                    logger.warning("Current configuration validation failed, falling back to default")
                    if self._default_config:
                        self._current_config = self._default_config
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Configuration refresh failed: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        with self._lock:
            self._config_cache.clear()
            logger.debug("Configuration cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'cache_size': len(self._config_cache),
                'cache_ttl': self._cache_ttl,
                'last_validation': self._last_validation,
                'validation_interval': self._validation_interval,
                'sources': {k: v is not None for k, v in self._config_sources.items()}
            }
    
    def _get_cached_config(self, cache_key: str) -> Optional[ProcessingConfig]:
        """Get cached configuration if valid."""
        with self._lock:
            if cache_key in self._config_cache:
                cache_entry = self._config_cache[cache_key]
                if time.time() - cache_entry.timestamp < self._cache_ttl:
                    logger.debug(f"Using cached configuration: {cache_key}")
                    return cache_entry.config
                else:
                    # Expired, remove from cache
                    del self._config_cache[cache_key]
            return None
    
    def _cache_config(self, cache_key: str, config: ProcessingConfig, source: str) -> None:
        """Cache a configuration."""
        with self._lock:
            cache_entry = ConfigurationCache(
                config=config,
                timestamp=time.time(),
                source=source
            )
            self._config_cache[cache_key] = cache_entry
            logger.debug(f"Cached configuration: {cache_key} from {source}")


# Global configuration manager instance
_config_manager = ConfigurationManager()


def get_configuration_manager() -> ConfigurationManager:
    """Get the global configuration manager instance."""
    return _config_manager


def set_global_configuration(config: ProcessingConfig) -> None:
    """Set the global configuration."""
    _config_manager.set_current_config(config)


def get_global_configuration() -> ProcessingConfig:
    """Get the global configuration."""
    return _config_manager.get_current_config() or _config_manager.get_default_config()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value from the global configuration."""
    return _config_manager.get_config_value(key, default)
