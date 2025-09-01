"""
Unified Configuration Management for Google Voice SMS Takeout XML Converter.

This module provides a single source of truth for all configuration options,
integrating command line arguments, configuration files, and environment variables.
"""

import os
from pathlib import Path
from typing import Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """
    Unified configuration model for the Google Voice SMS Converter.
    
    This model automatically handles:
    - Command line arguments (via Click integration)
    - Environment variables (with GVOICE_ prefix)
    - Configuration files (.env, config.json, etc.)
    - Type validation and conversion
    - Default values and constraints
    """
    
    model_config = SettingsConfigDict(
        env_prefix="GVOICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown fields
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,  # Allow case-insensitive env var matching
    )
    
    # ====================================================================
    # PROCESSING SETTINGS
    # ====================================================================
    
    processing_dir: Path = Field(
        default=Path.cwd().parent / "gvoice-convert",
        description="Directory containing Google Voice export data (Calls/ and Phones.vcf)"
    )
    
    output_format: Literal["html", "xml"] = Field(
        default="html",
        description="Output format for conversation files: html (default) or xml"
    )
    
    # ====================================================================
    # PERFORMANCE SETTINGS
    # ====================================================================
    
    max_workers: int = Field(
        default=16,
        ge=1,
        le=32,
        description="Maximum number of parallel workers"
    )
    
    chunk_size: int = Field(
        default=1000,
        ge=50,
        le=5000,
        description="Chunk size for parallel processing"
    )
    
    memory_threshold: int = Field(
        default=10000,
        ge=100,
        le=1000000,
        description="Threshold for switching to memory-efficient mode"
    )
    
    buffer_size: int = Field(
        default=32768,
        ge=1024,
        le=1048576,
        description="File I/O buffer size in bytes"
    )
    
    cache_size: int = Field(
        default=50000,
        ge=1000,
        le=1000000,
        description="LRU cache size for performance optimization"
    )
    
    batch_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Batch size for processing large datasets"
    )
    
    # ====================================================================
    # FEATURE FLAGS
    # ====================================================================
    
    enable_parallel_processing: bool = Field(
        default=True,
        description="Enable parallel processing for better performance"
    )
    
    enable_streaming_parsing: bool = Field(
        default=True,
        description="Enable streaming file parsing for large files"
    )
    
    enable_mmap_for_large_files: bool = Field(
        default=True,
        description="Enable memory mapping for large files (>5MB)"
    )
    
    enable_performance_monitoring: bool = Field(
        default=True,
        description="Enable performance monitoring and memory tracking"
    )
    
    enable_progress_logging: bool = Field(
        default=True,
        description="Enable progress logging during processing"
    )
    
    large_dataset: bool = Field(
        default=False,
        description="Enable optimizations for datasets with 50,000+ messages"
    )
    

    
    # ====================================================================
    # VALIDATION SETTINGS
    # ====================================================================
    
    enable_path_validation: bool = Field(
        default=True,
        description="Enable comprehensive path validation during processing"
    )
    
    enable_runtime_validation: bool = Field(
        default=True,
        description="Enable runtime validation during processing"
    )
    
    validation_interval: int = Field(
        default=10,
        ge=1,
        le=3600,
        description="Interval in seconds for runtime validation checks"
    )
    
    strict_mode: bool = Field(
        default=False,
        description="Enable strict parameter validation (catches errors early)"
    )
    
    # ====================================================================
    # LOGGING SETTINGS
    # ====================================================================
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Set specific log level"
    )
    
    log_filename: Optional[str] = Field(
        default="gvoice_converter.log",
        description="Custom log filename"
    )
    
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging (INFO level)"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug logging (DEBUG level)"
    )
    
    debug_attachments: bool = Field(
        default=False,
        description="Enable detailed debugging for attachment matching"
    )
    
    debug_paths: bool = Field(
        default=False,
        description="Enable detailed debugging for path resolution and validation"
    )
    
    # ====================================================================
    # TESTING SETTINGS
    # ====================================================================
    
    test_mode: bool = Field(
        default=True,
        description="Enable testing mode with limited processing (default: 100 entries)"
    )
    
    test_limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Number of entries to process in test mode"
    )
    
    full_run: bool = Field(
        default=False,
        description="Disable test mode and process all entries"
    )
    
    # ====================================================================
    # FILTERING SETTINGS
    # ====================================================================
    
    include_service_codes: bool = Field(
        default=False,
        description="Include service codes and short codes in processing"
    )
    
    filter_numbers_without_aliases: bool = Field(
        default=False,
        description="Filter out phone numbers that don't have aliases"
    )
    
    filter_non_phone_numbers: bool = Field(
        default=False,
        description="Filter out toll-free numbers and non-US numbers"
    )
    
    older_than: Optional[str] = Field(
        default=None,
        description="Filter out messages older than specified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
    )
    
    newer_than: Optional[str] = Field(
        default=None,
        description="Filter out messages newer than specified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
    )
    
    # ====================================================================
    # PHONE LOOKUP SETTINGS
    # ====================================================================
    
    phone_prompts: bool = Field(
        default=False,
        description="Enable interactive phone number alias prompts"
    )
    
    # ====================================================================
    # VALIDATORS
    # ====================================================================
    
    @field_validator('processing_dir', mode='before')
    @classmethod
    def validate_processing_dir(cls, v):
        """Convert string to Path and resolve to absolute path."""
        if isinstance(v, str):
            v = Path(v)
        if isinstance(v, Path):
            return v.resolve()
        return v
    
    @field_validator('older_than', 'newer_than')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format if provided."""
        if v is None:
            return v
        
        # Basic date format validation
        import re
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',  # YYYY-MM-DD HH:MM:SS
        ]
        
        if not any(re.match(pattern, v) for pattern in date_patterns):
            raise ValueError(
                f"Invalid date format: {v}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
            )
        
        return v
    
    @model_validator(mode='after')
    def validate_date_range(self):
        """Validate that date range is logical if both dates are provided."""
        older_than = self.older_than
        newer_than = self.newer_than
        
        if older_than and newer_than:
            try:
                from dateutil import parser
                older_date = parser.parse(older_than)
                newer_date = parser.parse(newer_than)
                
                if older_date >= newer_date:
                    raise ValueError(
                        f"Invalid date range: older_than ({older_than}) must be before newer_than ({newer_than})"
                    )
            except Exception as e:
                raise ValueError(f"Date validation error: {e}")
        
        return self
    
    @model_validator(mode='after')
    def validate_test_mode_conflicts(self):
        """Validate that test mode settings don't conflict."""
        # Only modify values if there's an actual conflict
        # This validator should not change default behavior
        return self
    
    @model_validator(mode='after')
    def validate_cli_conflicts(self):
        """Validate that CLI options don't conflict with each other."""
        errors = []
        

        
        # Critical conflict: full-run + test-limit
        # Detect if test_limit was explicitly set to a non-default value while full_run is True
        if self.full_run and self.test_limit != 100:  # 100 is the default test_limit
            errors.append(
                "Conflicting options: --full-run and --test-limit cannot be used together.\n"
                "  • --full-run means 'process all entries without test mode limitations'\n"
                "  • --test-limit means 'limit processing to N entries in test mode'\n"
                "  • These are mutually exclusive concepts\n"
                "  • Use --full-run to process all entries, or use --test-limit without --full-run for test mode"
            )
        
        # Critical conflict: full-run + test-mode
        # Detect if test_mode was explicitly set to True while full_run is True
        if self.full_run and self.test_mode:
            errors.append(
                "Conflicting options: --full-run and --test-mode cannot be used together.\n"
                "  • --full-run means 'process all entries without test mode limitations'\n"
                "  • --test-mode means 'enable testing mode with limited processing'\n"
                "  • These are mutually exclusive concepts\n"
                "  • Use --full-run to process all entries, or use --test-mode without --full-run for test mode"
            )
        
        # Critical conflict: verbose + debug
        if self.verbose and self.debug:
            errors.append(
                "Conflicting options: --verbose and --debug cannot be used together.\n"
                "  • --verbose sets logging to INFO level\n"
                "  • --debug sets logging to DEBUG level (includes verbose)\n"
                "  • Use --debug for maximum detail, or --verbose for moderate detail"
            )
        
        if errors:
            raise ValueError("\n\n".join(errors))
        
        return self
    
    @model_validator(mode='after')
    def validate_logging_conflicts(self):
        """Validate logging settings don't conflict."""
        if self.debug:
            self.verbose = False
            self.log_level = 'DEBUG'
        elif self.verbose:
            self.log_level = 'INFO'
        
        return self
    
    # ====================================================================
    # COMPUTED PROPERTIES
    # ====================================================================
    
    @property
    def is_test_mode(self) -> bool:
        """Determine if we're in test mode."""
        return self.test_mode and not self.full_run
    
    @property
    def effective_log_level(self) -> str:
        """Get the effective log level considering debug/verbose flags."""
        if self.debug:
            return 'DEBUG'
        elif self.verbose:
            return 'INFO'
        return self.log_level
    
    @property
    def effective_test_limit(self) -> int:
        """Get the effective test limit."""
        if self.full_run:
            return 10000  # Maximum allowed value for full run mode
        return self.test_limit
    
    # ====================================================================
    # UTILITY METHODS
    # ====================================================================
    
    def get_processing_directory(self) -> Path:
        """Get the resolved processing directory."""
        return self.processing_dir.resolve()
    
    def get_output_directory(self) -> Path:
        """Get the output directory (conversations subdirectory)."""
        return self.get_processing_directory() / "conversations"
    
    def get_attachments_directory(self) -> Path:
        """Get the attachments directory."""
        return self.get_output_directory() / "attachments"
    
    def get_log_file_path(self) -> Path:
        """Get the full path to the log file."""
        if self.log_filename:
            return self.get_processing_directory() / self.log_filename
        return self.get_processing_directory() / "gvoice_converter.log"
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return self.model_dump(exclude_none=True)
    
    def to_env_file(self) -> str:
        """Generate .env file content from current configuration."""
        lines = ["# Google Voice SMS Converter Configuration"]
        lines.append("# Generated automatically - modify as needed\n")
        
        for field_name, field_info in self.model_fields.items():
            if field_name in ['model_config', 'model_fields']:
                continue
            
            value = getattr(self, field_name)
            if value is not None:
                if isinstance(value, Path):
                    value = str(value)
                elif isinstance(value, bool):
                    value = str(value).lower()
                else:
                    value = str(value)
                
                lines.append(f"{field_name.upper()}={value}")
        
        return "\n".join(lines)
    
    def validate_processing_directory(self) -> bool:
        """Validate that the processing directory has the expected structure."""
        processing_dir = self.get_processing_directory()
        
        if not processing_dir.exists():
            return False
        
        # Check for required subdirectories and files
        calls_dir = processing_dir / "Calls"
        phones_vcf = processing_dir / "Phones.vcf"
        
        return calls_dir.exists() and phones_vcf.exists()
    
    def get_validation_errors(self) -> list:
        """Get a list of validation errors for the current configuration."""
        errors = []
        
        try:
            # Validate the model
            self.model_validate(self.model_dump())
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        # Check processing directory structure
        if not self.validate_processing_directory():
            errors.append(
                f"Processing directory {self.processing_dir} does not contain required structure "
                "(Calls/ subdirectory and Phones.vcf file)"
            )
        
        return errors


# ====================================================================
# FACTORY FUNCTIONS
# ====================================================================

def create_default_config() -> AppConfig:
    """Create a configuration with default values."""
    return AppConfig()


def create_config_from_env() -> AppConfig:
    """Create a configuration from environment variables."""
    return AppConfig()


def create_config_from_file(config_file: Union[str, Path]) -> AppConfig:
    """Create a configuration from a file."""
    config_file = Path(config_file)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    # Load configuration based on file extension
    if config_file.suffix == '.json':
        import json
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    elif config_file.suffix == '.yaml' or config_file.suffix == '.yml':
        import yaml
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
    elif config_file.suffix == '.toml':
        import tomllib
        with open(config_file, 'rb') as f:
            config_data = tomllib.load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
    
    return AppConfig(**config_data)


def merge_configs(*configs: AppConfig) -> AppConfig:
    """Merge multiple configurations, later configs override earlier ones."""
    if not configs:
        return create_default_config()
    
    # Start with the first config
    merged = configs[0].model_dump()
    
    # Override with subsequent configs
    for config in configs[1:]:
        config_dict = config.model_dump(exclude_none=True)
        # Only override non-None values
        for key, value in config_dict.items():
            if value is not None:
                merged[key] = value
    
    return AppConfig(**merged)


# ====================================================================
# CONFIGURATION PRESETS
# ====================================================================

def create_high_performance_config() -> AppConfig:
    """Create a configuration optimized for high performance."""
    return AppConfig(
        max_workers=32,
        chunk_size=2000,
        buffer_size=65536,
        cache_size=100000,
        batch_size=2000,
        enable_parallel_processing=True,
        enable_streaming_parsing=True,
        enable_mmap_for_large_files=True,
        enable_performance_monitoring=True
    )


def create_memory_efficient_config() -> AppConfig:
    """Create a configuration optimized for memory efficiency."""
    return AppConfig(
        max_workers=4,
        chunk_size=100,
        buffer_size=4096,
        cache_size=1000,
        batch_size=100,
        enable_parallel_processing=False,
        enable_streaming_parsing=True,
        enable_mmap_for_large_files=False,
        enable_performance_monitoring=True
    )


def create_test_config() -> AppConfig:
    """Create a configuration optimized for testing."""
    return AppConfig(
        test_mode=True,
        test_limit=10,
        max_workers=2,
        chunk_size=100,  # Minimum valid value
        buffer_size=1024,
        cache_size=1000,  # Minimum valid value
        batch_size=100,   # Minimum valid value
        enable_parallel_processing=False,
        enable_streaming_parsing=False,
        enable_mmap_for_large_files=False,
        enable_performance_monitoring=False,
        log_level="DEBUG",
        debug=True,
        strict_mode=True
    )

