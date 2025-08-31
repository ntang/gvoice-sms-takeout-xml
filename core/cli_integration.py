"""
Click CLI Integration for Google Voice SMS Takeout XML Converter.

This module provides automatic CLI generation from the Pydantic configuration model,
ensuring perfect synchronization between configuration and command line arguments.
"""

import click
from typing import Any, Dict, List, Optional, Type, Literal
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from .unified_config import AppConfig


def get_field_type_info(field_type: Type) -> tuple:
    """
    Extract type information from a Pydantic field type.
    
    Returns:
        tuple: (base_type, is_optional, is_literal, literal_values)
    """
    # Handle Optional types
    is_optional = False
    if hasattr(field_type, '__origin__') and field_type.__origin__ is Optional:
        is_optional = True
        # Get the actual type from Optional[T]
        if hasattr(field_type, '__args__'):
            field_type = field_type.__args__[0]
    
    # Handle Literal types
    is_literal = False
    literal_values = []
    if hasattr(field_type, '__origin__') and field_type.__origin__ is Literal:
        is_literal = True
        literal_values = field_type.__args__
        field_type = type(literal_values[0]) if literal_values else str
    
    return field_type, is_optional, is_literal, literal_values


def create_click_option_from_field(field_name: str, field_info: FieldInfo, field_type: Type) -> click.Option:
    """
    Create a Click option from a Pydantic field.
    
    Args:
        field_name: Name of the field
        field_info: Pydantic FieldInfo object
        field_type: Python type of the field
        
    Returns:
        click.Option: Click option object
    """
    # Get field metadata and handle default values properly
    if hasattr(field_info, 'default_factory') and field_info.default_factory is not None:
        # Use default_factory to get the actual default value
        try:
            default = field_info.default_factory()
        except Exception:
            default = None
    else:
        default = field_info.default
    
    # Handle PydanticUndefined
    if str(default) == 'PydanticUndefined':
        default = None
    
    description = field_info.description or f"Set {field_name}"
    
    # Convert field name to CLI option name
    option_name = f"--{field_name.replace('_', '-')}"
    
    # Get type information
    base_type, is_optional, is_literal, literal_values = get_field_type_info(field_type)
    
    # Determine Click parameter type
    if base_type == bool:
        # Boolean fields become flags
        return click.Option(
            [option_name],
            is_flag=True,
            default=default,
            help=description,
            show_default=True
        )
    
    elif base_type == int:
        # Integer fields with validation
        # Extract min/max from field constraints
        min_val = None
        max_val = None
        if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
            min_val = field_info.json_schema_extra.get('minimum')
            max_val = field_info.json_schema_extra.get('maximum')
        
        return click.Option(
            [option_name],
            type=click.IntRange(min=min_val, max=max_val) if min_val or max_val else int,
            default=default,
            help=description,
            show_default=True
        )
    
    elif base_type == float:
        # Float fields with validation
        min_val = None
        max_val = None
        if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
            min_val = field_info.json_schema_extra.get('minimum')
            max_val = field_info.json_schema_extra.get('maximum')
        
        return click.Option(
            [option_name],
            type=click.FloatRange(min=min_val, max=max_val) if min_val or max_val else float,
            default=default,
            help=description,
            show_default=True
        )
    
    elif base_type == Path:
        # Path fields
        return click.Option(
            [option_name],
            type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
            default=default,
            help=description,
            show_default=True
        )
    
    elif is_literal:
        # Literal fields become choice options
        return click.Option(
            [option_name],
            type=click.Choice([str(v) for v in literal_values]),
            default=str(default) if default is not None else None,
            help=description,
            show_default=True
        )
    
    elif base_type == str:
        # String fields
        return click.Option(
            [option_name],
            type=str,
            default=default,
            help=description,
            show_default=True
        )
    
    else:
        # Fallback for other types
        return click.Option(
            [option_name],
            type=str,
            default=str(default) if default is not None else None,
            help=description,
            show_default=True
        )


def create_click_command_from_config(config_class: Type[AppConfig]) -> click.Command:
    """
    Create a Click command from a Pydantic configuration model.
    
    Args:
        config_class: The Pydantic configuration class
        
    Returns:
        click.Command: Click command object with all options
    """
    
    def command_callback(**kwargs):
        """Callback function that creates and validates configuration."""
        try:
            # Create configuration from command line arguments
            config = config_class(**kwargs)
            
            # Validate configuration
            validation_errors = config.get_validation_errors()
            if validation_errors:
                click.echo("Configuration validation errors:", err=True)
                for error in validation_errors:
                    click.echo(f"  ❌ {error}", err=True)
                raise click.Abort()
            
            # Store configuration in click context for use in other functions
            click.get_current_context().obj = config
            
            return config
            
        except Exception as e:
            click.echo(f"Configuration error: {e}", err=True)
            raise click.Abort()
    
    # Create command with automatic help text
    command = click.Command(
        name="gvoice-converter",
        help="Convert Google Voice HTML export files to SMS backup XML format",
        callback=command_callback
    )
    
    # Add all fields as options
    for field_name, field_info in config_class.model_fields.items():
        # Skip internal Pydantic fields
        if field_name in ['model_config', 'model_fields']:
            continue
        
        # Get the field type from the model
        field_type = config_class.model_fields[field_name].annotation
        
        # Create Click option
        option = create_click_option_from_field(field_name, field_info, field_type)
        
        # Add option to command
        command.params.append(option)
    
    return command


def create_click_group_from_config(config_class: Type[AppConfig]) -> click.Group:
    """
    Create a Click group with subcommands from a Pydantic configuration model.
    
    Args:
        config_class: The Pydantic configuration class
        
    Returns:
        click.Group: Click group object with configuration and subcommands
    """
    
    @click.group()
    @click.pass_context
    def cli_group(ctx, **kwargs):
        """Google Voice SMS Takeout XML Converter."""
        # Initialize with configuration from command line arguments
        ctx.ensure_object(dict)
        try:
            ctx.obj['config'] = config_class(**kwargs)
        except Exception as e:
            click.echo(f"Configuration error: {e}", err=True)
            raise click.Abort()
    
    # Add configuration options to the group
    for field_name, field_info in config_class.model_fields.items():
        # Skip internal Pydantic fields
        if field_name in ['model_config', 'model_fields']:
            continue
        
        # Get the field type from the model
        field_type = config_class.model_fields[field_name].annotation
        
        # Create Click option
        option = create_click_option_from_field(field_name, field_info, field_type)
        
        # Add option to group
        cli_group.params.append(option)
    
    # Add subcommands
    @cli_group.command()
    @click.pass_context
    def convert(ctx):
        """Convert Google Voice export files."""
        config = ctx.obj['config']
        click.echo(f"Converting files from: {config.processing_dir}")
        # This would call the main conversion logic
    
    @cli_group.command()
    @click.pass_context
    def validate(ctx):
        """Validate configuration and processing directory."""
        config = ctx.obj['config']
        validation_errors = config.get_validation_errors()
        
        if not validation_errors:
            click.echo("✅ Configuration is valid")
            click.echo(f"Processing directory: {config.processing_dir}")
            click.echo(f"Output format: {config.output_format}")
        else:
            click.echo("❌ Configuration validation errors:", err=True)
            for error in validation_errors:
                click.echo(f"  - {error}", err=True)
    
    @cli_group.command()
    @click.pass_context
    def config_export(ctx):
        """Export current configuration to various formats."""
        config = ctx.obj['config']
        
        # Export to .env format
        env_content = config.to_env_file()
        click.echo("Environment file (.env) format:")
        click.echo(env_content)
        
        # Export to JSON format
        json_content = config.to_dict()
        click.echo("\nJSON format:")
        click.echo(json_content)
    
    @cli_group.command()
    @click.pass_context
    def create_config(ctx):
        """Create a sample configuration file."""
        config = ctx.obj['config']
        
        # Create .env file
        env_content = config.to_env_file()
        env_file = Path(".env")
        
        if env_file.exists():
            if not click.confirm(f"File {env_file} already exists. Overwrite?"):
                return
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        click.echo(f"✅ Created configuration file: {env_file}")
        click.echo("You can now modify the values in this file and they will be automatically loaded.")
    
    return cli_group


def get_config_from_context() -> Optional[AppConfig]:
    """
    Get the configuration object from the current Click context.
    
    Returns:
        AppConfig or None: The configuration object if available
    """
    try:
        ctx = click.get_current_context()
        if ctx.obj and isinstance(ctx.obj, dict) and 'config' in ctx.obj:
            return ctx.obj['config']
        elif hasattr(ctx.obj, 'model_fields'):  # Direct config object
            return ctx.obj
        return None
    except RuntimeError:
        # Not in a Click context
        return None


def create_legacy_compatibility_layer(config: AppConfig) -> Dict[str, Any]:
    """
    Create a compatibility layer for existing code that expects the old configuration format.
    
    Args:
        config: The new AppConfig object
        
    Returns:
        dict: Dictionary with old-style configuration keys
    """
    return {
        # Processing settings
        'processing_dir': str(config.processing_dir),
        'output_format': config.output_format,
        
        # Performance settings
        'max_workers': config.max_workers,
        'chunk_size': config.chunk_size,
        'memory_threshold': config.memory_threshold,
        'buffer_size': config.buffer_size,
        'cache_size': config.cache_size,
        'batch_size': config.batch_size,
        
        # Feature flags
        'enable_parallel_processing': config.enable_parallel_processing,
        'enable_streaming_parsing': config.enable_streaming_parsing,
        'enable_mmap_for_large_files': config.enable_mmap_for_large_files,
        'enable_performance_monitoring': config.enable_performance_monitoring,
        'enable_progress_logging': config.enable_progress_logging,
        
        # Validation settings
        'enable_path_validation': config.enable_path_validation,
        'enable_runtime_validation': config.enable_runtime_validation,
        'validation_interval': config.validation_interval,
        'strict_mode': config.strict_mode,
        
        # Logging settings
        'log_level': config.effective_log_level,
        'log_filename': config.log_filename,
        'verbose': config.verbose,
        'debug': config.debug,
        'debug_attachments': config.debug_attachments,
        'debug_paths': config.debug_paths,
        
        # Testing settings
        'test_mode': config.is_test_mode,
        'test_limit': config.effective_test_limit,
        'full_run': config.full_run,
        
        # Filtering settings
        'include_service_codes': config.include_service_codes,
        'filter_numbers_without_aliases': config.filter_numbers_without_aliases,
        'filter_non_phone_numbers': config.filter_non_phone_numbers,
        'older_than': config.older_than,
        'newer_than': config.newer_than,
        
        # Phone lookup settings
        'phone_prompts': config.phone_prompts,
    }


# ====================================================================
# UTILITY FUNCTIONS FOR EXISTING CODE INTEGRATION
# ====================================================================

def create_config_from_legacy_args(args: Any) -> AppConfig:
    """
    Create a new AppConfig from legacy argparse arguments.
    
    Args:
        args: argparse.Namespace or similar object with old-style arguments
        
    Returns:
        AppConfig: New configuration object
    """
    # Map old argument names to new configuration fields
    config_data = {}
    
    # Processing settings
    if hasattr(args, 'processing_dir'):
        config_data['processing_dir'] = args.processing_dir
    
    if hasattr(args, 'output_format'):
        config_data['output_format'] = args.output_format
    
    # Performance settings
    if hasattr(args, 'workers'):
        config_data['max_workers'] = args.workers
    
    if hasattr(args, 'chunk_size'):
        config_data['chunk_size'] = args.chunk_size
    
    if hasattr(args, 'memory_threshold'):
        config_data['memory_threshold'] = args.memory_threshold
    
    if hasattr(args, 'buffer_size'):
        config_data['buffer_size'] = args.buffer_size
    
    if hasattr(args, 'cache_size'):
        config_data['cache_size'] = args.cache_size
    
    if hasattr(args, 'batch_size'):
        config_data['batch_size'] = args.batch_size
    
    # Feature flags
    if hasattr(args, 'no_parallel'):
        config_data['enable_parallel_processing'] = not args.no_parallel
    
    if hasattr(args, 'no_streaming'):
        config_data['enable_streaming_parsing'] = not args.no_streaming
    
    if hasattr(args, 'no_mmap'):
        config_data['enable_mmap_for_large_files'] = not args.no_mmap
    
    if hasattr(args, 'no_performance'):
        config_data['enable_performance_monitoring'] = not args.no_performance
    
    if hasattr(args, 'no_progress'):
        config_data['enable_progress_logging'] = not args.no_progress
    
    # Validation settings
    if hasattr(args, 'strict_mode'):
        config_data['strict_mode'] = args.strict_mode
    
    if hasattr(args, 'validate_paths'):
        config_data['enable_path_validation'] = args.validate_paths
    
    # Logging settings
    if hasattr(args, 'log_level'):
        config_data['log_level'] = args.log_level
    
    if hasattr(args, 'log'):
        config_data['log_filename'] = args.log
    
    if hasattr(args, 'verbose'):
        config_data['verbose'] = args.verbose
    
    if hasattr(args, 'debug'):
        config_data['debug'] = args.debug
    
    if hasattr(args, 'debug_attachments'):
        config_data['debug_attachments'] = args.debug_attachments
    
    if hasattr(args, 'debug_paths'):
        config_data['debug_paths'] = args.debug_paths
    
    # Testing settings
    if hasattr(args, 'test_mode'):
        config_data['test_mode'] = args.test_mode
    
    if hasattr(args, 'output_format'):
        config_data['output_format'] = args.output_format
    
    if hasattr(args, 'test_limit'):
        config_data['test_limit'] = args.test_limit
    
    if hasattr(args, 'full_run'):
        config_data['full_run'] = args.full_run
    
    # Filtering settings
    if hasattr(args, 'include_service_codes'):
        config_data['include_service_codes'] = args.include_service_codes
    
    if hasattr(args, 'filter_no_alias'):
        config_data['filter_numbers_without_aliases'] = args.filter_no_alias
    
    if hasattr(args, 'exclude_no_alias'):
        config_data['filter_numbers_without_aliases'] = args.exclude_no_alias
    
    if hasattr(args, 'filter_non_phone'):
        config_data['filter_non_phone_numbers'] = args.filter_non_phone
    
    if hasattr(args, 'older_than'):
        config_data['older_than'] = args.older_than
    
    if hasattr(args, 'newer_than'):
        config_data['newer_than'] = args.newer_than
    
    # Phone lookup settings
    if hasattr(args, 'phone_prompts'):
        config_data['phone_prompts'] = args.phone_prompts
    
    # Create and return configuration
    return AppConfig(**config_data)

