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
    output_format: Literal["html"] = "html"
    
    # Performance Settings (optimized defaults - no configuration needed)
    # max_workers, batch_size, buffer_size, etc. are now hardcoded in shared_constants.py
    # for optimal performance on high-end systems (16GB+ RAM, 8+ cores, 20-50k files)
    
    # Validation Settings
    enable_path_validation: bool = True
    enable_runtime_validation: bool = True
    strict_mode: bool = False
    
    # Phone Lookup Settings
    enable_phone_prompts: bool = False
    skip_filtered_contacts: bool = True
    phone_lookup_file: Optional[Path] = None
    
    # Filtering Settings
    include_service_codes: bool = False
    filter_numbers_without_aliases: bool = False
    filter_non_phone_numbers: bool = False
    filter_groups_with_all_filtered: bool = True  # Default: enabled (new behavior)
    
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
    
    # Large Dataset Optimizations (now handled automatically by shared_constants.py)
    large_dataset: bool = False
    
    # Additional CLI Options
    validation_interval: int = 1000
    log_filename: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Ensure output_dir is set if not provided
        if self.output_dir is None:
            self.output_dir = self.processing_dir / "conversations"
        
        # Ensure phone_lookup_file is set if not provided
        if self.phone_lookup_file is None:
            self.phone_lookup_file = self.processing_dir / "phone_lookup.txt"
        
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
        # Performance settings are now hardcoded in shared_constants.py for optimal defaults
    
    def _validate_date_ranges(self) -> None:
        """Validate date filtering logic."""
        if self.older_than and self.newer_than:
            if self.older_than >= self.newer_than:
                raise ValueError(
                    f"older_than ({self.older_than}) must be before newer_than ({self.newer_than})"
                )
    
    def _validate_output_format(self) -> None:
        """Validate output format setting."""
        if self.output_format != "html":
            raise ValueError(f"output_format must be 'html', got {self.output_format}")
    
    def _log_configuration_summary(self) -> None:
        """Log a summary of the configuration for debugging."""
        logger.debug("Configuration Summary:")
        logger.debug(f"  Processing Directory: {self.processing_dir}")
        logger.debug(f"  Output Directory: {self.output_dir}")
        logger.debug(f"  Output Format: {self.output_format}")
        logger.debug(f"  Phone Lookup File: {self.phone_lookup_file}")
        # Performance settings are now hardcoded
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
        
        if "phone_lookup_file" in config_dict and config_dict["phone_lookup_file"]:
            config_dict["phone_lookup_file"] = Path(config_dict["phone_lookup_file"])
        
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
    
    def get_validation_errors(self) -> List[str]:
        """Get validation errors for the configuration.
        
        Returns:
            List of validation error messages, empty if valid
        """
        errors = []
        
        # Check required fields
        if not self.processing_dir:
            errors.append("Processing directory is required")
        
        # Check processing directory exists and is accessible
        if self.processing_dir:
            try:
                if not self.processing_dir.exists():
                    errors.append(f"Processing directory does not exist: {self.processing_dir}")
                elif not self.processing_dir.is_dir():
                    errors.append(f"Processing path is not a directory: {self.processing_dir}")
                else:
                    # Test read access
                    try:
                        next(self.processing_dir.iterdir())
                    except PermissionError:
                        errors.append(f"No read permission for processing directory: {self.processing_dir}")
            except Exception as e:
                errors.append(f"Error accessing processing directory: {e}")
        
        # Check numeric fields are positive
        # Performance settings are now hardcoded in shared_constants.py
        if self.test_limit <= 0:
            errors.append("test_limit must be positive")
        
        # Check output format is valid (HTML only)
        if self.output_format != 'html':
            errors.append(f"Invalid output format: {self.output_format}")
        
        # Check log level is valid
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")
        
        return errors


class ConfigurationDefaults:
    """Default configuration values and presets."""
    
    @staticmethod
    def get_defaults() -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            # Performance settings are now hardcoded in shared_constants.py
            # Performance features are now always enabled
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
            # Batch processing is now always enabled
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
        }
    
    @staticmethod
    def get_production_presets() -> Dict[str, Any]:
        """Get production mode configuration presets."""
        return {
            "test_mode": False,
            "full_run": True,
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
            # Performance settings are now hardcoded
            # Performance features are now always enabled
            'enable_path_validation': 'enable_path_validation',
            'enable_runtime_validation': 'enable_runtime_validation',
            'strict_mode': 'strict_mode',
            'phone_prompts': 'enable_phone_prompts',
            'phone_lookup_file': 'phone_lookup_file',
            'skip_filtered_contacts': 'skip_filtered_contacts',
            'include_service_codes': 'include_service_codes',
            'filter_numbers_without_aliases': 'filter_numbers_without_aliases',
            'filter_non_phone_numbers': 'filter_non_phone_numbers',
            'filter_groups_with_all_filtered': 'filter_groups_with_all_filtered',
            'test_mode': 'test_mode',
            'test_limit': 'test_limit',
            'full_run': 'full_run',
            'log_level': 'log_level',
            'verbose': 'verbose',
            'debug': 'debug',
            'debug_attachments': 'debug_attachments',
            'debug_paths': 'debug_paths',
            'large_dataset': 'large_dataset',
            # Batch processing is now always enabled
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
            # Performance settings are now hardcoded in shared_constants.py
            # Performance features are now always enabled for optimal defaults
            'enable_path_validation': os.environ.get('GVOICE_ENABLE_PATH_VALIDATION', 'true').lower() == 'true',
            'enable_runtime_validation': os.environ.get('GVOICE_ENABLE_RUNTIME_VALIDATION', 'true').lower() == 'true',
            'strict_mode': os.environ.get('GVOICE_STRICT_MODE', 'false').lower() == 'true',
            'enable_phone_prompts': os.environ.get('GVOICE_ENABLE_PHONE_PROMPTS', 'false').lower() == 'true',
            'skip_filtered_contacts': os.environ.get('GVOICE_SKIP_FILTERED_CONTACTS', 'true').lower() == 'true',
            'phone_lookup_file': os.environ.get('GVOICE_PHONE_LOOKUP_FILE'),
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
            # Batch processing is now always enabled
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

