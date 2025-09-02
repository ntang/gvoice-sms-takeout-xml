"""
Processing Configuration Module for SMS/MMS processing system.

This module implements the Configuration Object Pattern to replace
global variables and function parameters with a centralized, validated
configuration system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    """
    Centralized configuration for SMS/MMS processing operations.
    
    This class replaces global variables and function parameters with
    a single, validated configuration object that can be passed through
    the system.
    """
    
    # Core Processing Settings
    processing_dir: Path
    output_dir: Optional[Path] = None
    output_format: Literal["html", "xml"] = "html"
    
    # Performance Settings
    max_workers: int = 16
    chunk_size: int = 1000
    batch_size: int = 1000
    buffer_size: int = 32768
    cache_size: int = 25000
    memory_threshold: int = 10000
    
    # Feature Flags
    enable_parallel_processing: bool = True
    enable_streaming_parsing: bool = True
    enable_mmap_for_large_files: bool = True
    enable_performance_monitoring: bool = True
    enable_progress_logging: bool = True
    
    # Validation Settings
    enable_path_validation: bool = True
    enable_runtime_validation: bool = True
    strict_mode: bool = False
    
    # Phone Lookup Settings
    enable_phone_prompts: bool = False
    skip_filtered_contacts: bool = True
    
    # Filtering Settings
    include_service_codes: bool = False
    filter_numbers_without_aliases: bool = False
    filter_non_phone_numbers: bool = False
    
    # Date Filtering
    older_than: Optional[datetime] = None
    newer_than: Optional[datetime] = None
    
    # Test Mode
    test_mode: bool = False
    test_limit: int = 100
    full_run: bool = False
    
    # Debug Settings
    log_level: str = "INFO"
    verbose: bool = False
    debug: bool = False
    debug_attachments: bool = False
    debug_paths: bool = False
    
    # Large Dataset Optimizations
    large_dataset: bool = False
    enable_batch_processing: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Ensure output_dir is set if not provided
        if self.output_dir is None:
            self.output_dir = self.processing_dir / "conversations"
        

        
        # Validate numeric constraints
        self._validate_numeric_constraints()
        
        # Validate date ranges
        self._validate_date_ranges()
        
        # Validate output format
        self._validate_output_format()
        
        # Log configuration summary
        self._log_configuration_summary()
    
    def _validate_numeric_constraints(self) -> None:
        """Validate numeric configuration values."""
        if self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
        
        if self.chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {self.chunk_size}")
        
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        
        if self.buffer_size < 1024:
            raise ValueError(f"buffer_size must be >= 1024, got {self.buffer_size}")
        
        if self.cache_size < 100:
            raise ValueError(f"cache_size must be >= 100, got {self.cache_size}")
        
        if self.memory_threshold < 100:
            raise ValueError(f"memory_threshold must be >= 100, got {self.memory_threshold}")
    
    def _validate_date_ranges(self) -> None:
        """Validate date filtering logic."""
        if self.older_than and self.newer_than:
            if self.older_than >= self.newer_than:
                raise ValueError(
                    f"older_than ({self.older_than}) must be before newer_than ({self.newer_than})"
                )
    
    def _validate_output_format(self) -> None:
        """Validate output format setting."""
        if self.output_format not in ["html", "xml"]:
            raise ValueError(f"output_format must be 'html' or 'xml', got {self.output_format}")
    
    def _log_configuration_summary(self) -> None:
        """Log a summary of the configuration for debugging."""
        logger.debug("Configuration Summary:")
        logger.debug(f"  Processing Directory: {self.processing_dir}")
        logger.debug(f"  Output Directory: {self.output_dir}")
        logger.debug(f"  Output Format: {self.output_format}")
        logger.debug(f"  Max Workers: {self.max_workers}")
        logger.debug(f"  Test Mode: {self.test_mode}")
        logger.debug(f"  Phone Prompts: {self.enable_phone_prompts}")
        logger.debug(f"  Strict Mode: {self.strict_mode}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        config_dict = {}
        
        for field_name, field_value in self.__dict__.items():
            # Skip internal flags
            if field_name.startswith('_'):
                continue
                
            if isinstance(field_value, Path):
                config_dict[field_name] = str(field_value)
            elif isinstance(field_value, datetime):
                config_dict[field_name] = field_value.isoformat()
            else:
                config_dict[field_name] = field_value
        
        return config_dict
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ProcessingConfig":
        """Create configuration from dictionary."""
        # Convert string paths back to Path objects
        if "processing_dir" in config_dict:
            config_dict["processing_dir"] = Path(config_dict["processing_dir"])
        
        if "output_dir" in config_dict and config_dict["output_dir"]:
            config_dict["output_dir"] = Path(config_dict["output_dir"])
        
        # Convert string dates back to datetime objects
        if "older_than" in config_dict and config_dict["older_than"]:
            config_dict["older_than"] = datetime.fromisoformat(config_dict["older_than"])
        
        if "newer_than" in config_dict and config_dict["newer_than"]:
            config_dict["newer_than"] = datetime.fromisoformat(config_dict["newer_than"])
        
        return cls(**config_dict)
    
    def get_effective_value(self, key: str, default: Any = None) -> Any:
        """Get effective configuration value with fallback to default."""
        return getattr(self, key, default)
    
    def is_test_mode(self) -> bool:
        """Check if test mode is enabled."""
        return self.test_mode and not self.full_run
    
    def get_test_limit(self) -> int:
        """Get effective test limit."""
        if self.is_test_mode():
            return self.test_limit
        return -1  # No limit
    
    def should_enable_phone_prompts(self) -> bool:
        """Check if phone prompts should be enabled."""
        return self.enable_phone_prompts and not self.test_mode
    
    def get_output_format(self) -> str:
        """Get effective output format."""
        return self.output_format
    
    def get_processing_directory(self) -> Path:
        """Get processing directory path."""
        return self.processing_dir
    
    def get_output_directory(self) -> Path:
        """Get output directory path."""
        return self.output_dir


class ConfigurationDefaults:
    """Default configuration values and presets."""
    
    @staticmethod
    def get_defaults() -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "max_workers": 16,
            "chunk_size": 1000,
            "batch_size": 1000,
            "buffer_size": 32768,
            "cache_size": 25000,
            "memory_threshold": 10000,
            "enable_parallel_processing": True,
            "enable_streaming_parsing": True,
            "enable_mmap_for_large_files": True,
            "enable_performance_monitoring": True,
            "enable_progress_logging": True,
            "enable_path_validation": True,
            "enable_runtime_validation": True,
            "strict_mode": False,
            "enable_phone_prompts": False,
            "skip_filtered_contacts": True,
            "include_service_codes": False,
            "filter_numbers_without_aliases": False,
            "filter_non_phone_numbers": False,
            "test_mode": False,
            "test_limit": 100,
            "full_run": False,
            "log_level": "INFO",
            "verbose": False,
            "debug": False,
            "debug_attachments": False,
            "debug_paths": False,
            "large_dataset": False,
            "enable_batch_processing": True,
        }
    
    @staticmethod
    def get_test_presets() -> Dict[str, Any]:
        """Get test mode configuration presets."""
        return {
            "test_mode": True,
            "test_limit": 100,
            "full_run": False,
            "enable_phone_prompts": False,
            "strict_mode": True,
            "enable_performance_monitoring": False,
        }
    
    @staticmethod
    def get_production_presets() -> Dict[str, Any]:
        """Get production mode configuration presets."""
        return {
            "test_mode": False,
            "full_run": True,
            "enable_performance_monitoring": True,
            "enable_progress_logging": True,
            "strict_mode": False,
        }


class ConfigurationBuilder:
    """Builds ProcessingConfig from various sources."""
    
    @classmethod
    def from_cli_args(cls, cli_args: Dict[str, Any]) -> ProcessingConfig:
        """
        Build configuration from CLI arguments.
        
        Args:
            cli_args: Dictionary of CLI argument values
            
        Returns:
            ProcessingConfig instance
        """
        # Extract processing directory (required)
        processing_dir = cli_args.get('processing_dir')
        if not processing_dir:
            raise ValueError("processing_dir is required")
        
        # Convert to Path if it's a string
        if isinstance(processing_dir, str):
            processing_dir = Path(processing_dir)
        
        # Build configuration with CLI values - only set explicitly provided values
        config_kwargs = {'processing_dir': processing_dir}
        
        # Map CLI argument names to configuration field names
        field_mapping = {
            'output_format': 'output_format',
            'max_workers': 'max_workers',
            'chunk_size': 'chunk_size',
            'batch_size': 'batch_size',
            'buffer_size': 'buffer_size',
            'cache_size': 'cache_size',
            'memory_threshold': 'memory_threshold',
            'enable_parallel_processing': 'enable_parallel_processing',
            'enable_streaming_parsing': 'enable_streaming_parsing',
            'enable_mmap_for_large_files': 'enable_mmap_for_large_files',
            'enable_performance_monitoring': 'enable_performance_monitoring',
            'enable_progress_logging': 'enable_progress_logging',
            'enable_path_validation': 'enable_path_validation',
            'enable_runtime_validation': 'enable_runtime_validation',
            'strict_mode': 'strict_mode',
            'phone_prompts': 'enable_phone_prompts',
            'skip_filtered_contacts': 'skip_filtered_contacts',
            'include_service_codes': 'include_service_codes',
            'filter_numbers_without_aliases': 'filter_numbers_without_aliases',
            'filter_non_phone_numbers': 'filter_non_phone_numbers',
            'test_mode': 'test_mode',
            'test_limit': 'test_limit',
            'full_run': 'full_run',
            'log_level': 'log_level',
            'verbose': 'verbose',
            'debug': 'debug',
            'debug_attachments': 'debug_attachments',
            'debug_paths': 'debug_paths',
            'large_dataset': 'large_dataset',
            'enable_batch_processing': 'enable_batch_processing',
        }
        
        # Only add CLI values that are explicitly provided
        for cli_key, config_key in field_mapping.items():
            if cli_key in cli_args:
                config_kwargs[config_key] = cli_args[cli_key]
        
        # Handle date filtering
        if cli_args.get('older_than'):
            try:
                from dateutil import parser
                config_kwargs['older_than'] = parser.parse(cli_args['older_than'])
            except Exception as e:
                logger.warning(f"Failed to parse older_than date: {e}")
        
        if cli_args.get('newer_than'):
            try:
                from dateutil import parser
                config_kwargs['newer_than'] = parser.parse(cli_args['newer_than'])
            except Exception as e:
                logger.warning(f"Failed to parse newer_than date: {e}")
        
        # Store the explicitly set CLI fields for later merging
        config = ProcessingConfig(**config_kwargs)
        config._explicit_cli_fields = set(config_kwargs.keys())
        return config
    
    @classmethod
    def from_environment(cls) -> ProcessingConfig:
        """
        Build configuration from environment variables.
        
        Returns:
            ProcessingConfig instance with environment-based values
        """
        import os
        
        # Get processing directory from environment
        processing_dir = os.environ.get('GVOICE_PROCESSING_DIR')
        if not processing_dir:
            raise ValueError("GVOICE_PROCESSING_DIR environment variable is required")
        
        config_kwargs = {
            'processing_dir': Path(processing_dir),
            'output_format': os.environ.get('GVOICE_OUTPUT_FORMAT', 'html'),
            'max_workers': int(os.environ.get('GVOICE_MAX_WORKERS', '16')),
            'chunk_size': int(os.environ.get('GVOICE_CHUNK_SIZE', '1000')),
            'batch_size': int(os.environ.get('GVOICE_BATCH_SIZE', '1000')),
            'buffer_size': int(os.environ.get('GVOICE_BUFFER_SIZE', '32768')),
            'cache_size': int(os.environ.get('GVOICE_CACHE_SIZE', '25000')),
            'memory_threshold': int(os.environ.get('GVOICE_MEMORY_THRESHOLD', '10000')),
            'enable_parallel_processing': os.environ.get('GVOICE_ENABLE_PARALLEL', 'true').lower() == 'true',
            'enable_streaming_parsing': os.environ.get('GVOICE_ENABLE_STREAMING', 'true').lower() == 'true',
            'enable_mmap_for_large_files': os.environ.get('GVOICE_ENABLE_MMAP', 'true').lower() == 'true',
            'enable_performance_monitoring': os.environ.get('GVOICE_ENABLE_MONITORING', 'true').lower() == 'true',
            'enable_progress_logging': os.environ.get('GVOICE_ENABLE_PROGRESS', 'true').lower() == 'true',
            'enable_path_validation': os.environ.get('GVOICE_ENABLE_PATH_VALIDATION', 'true').lower() == 'true',
            'enable_runtime_validation': os.environ.get('GVOICE_ENABLE_RUNTIME_VALIDATION', 'true').lower() == 'true',
            'strict_mode': os.environ.get('GVOICE_STRICT_MODE', 'false').lower() == 'true',
            'enable_phone_prompts': os.environ.get('GVOICE_ENABLE_PHONE_PROMPTS', 'false').lower() == 'true',
            'skip_filtered_contacts': os.environ.get('GVOICE_SKIP_FILTERED_CONTACTS', 'true').lower() == 'true',
            'include_service_codes': os.environ.get('GVOICE_INCLUDE_SERVICE_CODES', 'false').lower() == 'true',
            'filter_numbers_without_aliases': os.environ.get('GVOICE_FILTER_NUMBERS_WITHOUT_ALIASES', 'false').lower() == 'true',
            'filter_non_phone_numbers': os.environ.get('GVOICE_FILTER_NON_PHONE_NUMBERS', 'false').lower() == 'true',
            'test_mode': os.environ.get('GVOICE_TEST_MODE', 'false').lower() == 'true',
            'test_limit': int(os.environ.get('GVOICE_TEST_LIMIT', '100')),
            'full_run': os.environ.get('GVOICE_FULL_RUN', 'false').lower() == 'true',
            'log_level': os.environ.get('GVOICE_LOG_LEVEL', 'INFO'),
            'verbose': os.environ.get('GVOICE_VERBOSE', 'false').lower() == 'true',
            'debug': os.environ.get('GVOICE_DEBUG', 'false').lower() == 'true',
            'debug_attachments': os.environ.get('GVOICE_DEBUG_ATTACHMENTS', 'false').lower() == 'true',
            'debug_paths': os.environ.get('GVOICE_DEBUG_PATHS', 'false').lower() == 'true',
            'large_dataset': os.environ.get('GVOICE_LARGE_DATASET', 'false').lower() == 'true',
            'enable_batch_processing': os.environ.get('GVOICE_ENABLE_BATCH_PROCESSING', 'true').lower() == 'true',
        }
        
        return ProcessingConfig(**config_kwargs)
    
    @classmethod
    def merge_configs(cls, *configs: ProcessingConfig) -> ProcessingConfig:
        """
        Merge multiple configurations with precedence rules.
        
        Later configurations override earlier ones.
        
        Args:
            *configs: ProcessingConfig instances to merge
            
        Returns:
            Merged ProcessingConfig instance
        """
        if not configs:
            raise ValueError("At least one configuration must be provided")
        
        if len(configs) == 1:
            return configs[0]
        
        # Start with the first config
        merged_dict = configs[0].to_dict()
        
        # Override with subsequent configs
        for config in configs[1:]:
            config_dict = config.to_dict()
            for key, value in config_dict.items():
                # Only override if this field was explicitly set in the CLI config
                if hasattr(config, '_explicit_cli_fields') and key in config._explicit_cli_fields:
                    merged_dict[key] = value
                elif not hasattr(config, '_explicit_cli_fields'):
                    # For non-CLI configs, override all non-None values
                    if value is not None:
                        merged_dict[key] = value
        
        return ProcessingConfig.from_dict(merged_dict)
    
    @classmethod
    def create_with_presets(cls, processing_dir: Path, preset: str = "default") -> ProcessingConfig:
        """
        Create configuration with preset values.
        
        Args:
            processing_dir: Processing directory path
            preset: Preset name ('default', 'test', 'production')
            
        Returns:
            ProcessingConfig instance with preset values
        """
        if preset == "test":
            preset_values = ConfigurationDefaults.get_test_presets()
        elif preset == "production":
            preset_values = ConfigurationDefaults.get_production_presets()
        else:
            preset_values = ConfigurationDefaults.get_defaults()
        
        config_kwargs = {
            'processing_dir': processing_dir,
            **preset_values
        }
        
        return ProcessingConfig(**config_kwargs)

