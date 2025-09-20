#!/usr/bin/env python3
"""
Google Voice SMS Takeout HTML Converter - CLI Interface (New Configuration System)

This module provides a CLI interface that integrates with the new configuration
system with the new configuration architecture.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
import dateutil.parser

# Import our new configuration system
from core.processing_config import ProcessingConfig, ConfigurationBuilder
from core.configuration_manager import get_configuration_manager, set_global_configuration
from core.sms_patch import patch_sms_module, unpatch_sms_module, is_sms_module_patched

# Import the main conversion logic from sms.py - moved to avoid circular import


def setup_logging(config: ProcessingConfig) -> None:
    """Set up logging based on configuration."""
    # Determine log level
    if config.debug:
        log_level = logging.DEBUG
    elif config.verbose:
        log_level = logging.INFO
    else:
        log_level = getattr(logging, config.log_level.upper())
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Add file handler if log filename is specified
    if config.log_filename:
        log_file = config.processing_dir / config.log_filename
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
    
    # Set module-specific logging levels
    if config.debug:
        logging.getLogger("concurrent.futures").setLevel(logging.INFO)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
    
    # Log the configured log level
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Log level set to: {logging.getLevelName(log_level)}")


def patch_sms_module_with_config(config: ProcessingConfig) -> None:
    """Patch the SMS module with the new configuration system.
    
    This function uses our new SMS module patcher to integrate the configuration
    system with the existing sms.py module.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Check if module is already patched
        if is_sms_module_patched():
            logger.warning("⚠️  SMS module is already patched - unpatching first")
            # Get the configuration manager to find active patchers
            manager = get_configuration_manager()
            active_patchers = manager.get_active_patchers()
            for patcher in active_patchers:
                unpatch_sms_module(patcher)
        
        # Patch the module with new configuration
        logger.info("🔧 Patching SMS module with new configuration system...")
        patcher = patch_sms_module(config)
        
        # Set as global configuration
        set_global_configuration(config)
        
        logger.info("✅ SMS module successfully patched with new configuration")
        logger.info(f"  Processing directory: {config.processing_dir}")
        logger.info(f"  Output format: {config.output_format}")
        logger.info(f"  Test mode: {config.test_mode}")
        if config.test_mode:
            logger.info(f"  Test limit: {config.test_limit}")
        
        return patcher
        
    except Exception as e:
        logger.error(f"❌ Failed to patch SMS module: {e}")
        raise


def validate_and_setup(config: ProcessingConfig) -> bool:
    """Validate configuration and set up processing paths."""
    logger = logging.getLogger(__name__)
    
    try:
        # Validate processing directory
        if not config.processing_dir.exists():
            logger.error(f"❌ Processing directory does not exist: {config.processing_dir}")
            return False
        
        if not config.processing_dir.is_dir():
            logger.error(f"❌ Processing path is not a directory: {config.processing_dir}")
            return False
        
        # Check for expected subdirectories
        calls_dir = config.processing_dir / "Calls"
        if not calls_dir.exists():
            logger.warning(f"⚠️  Calls directory not found: {calls_dir}")
            logger.warning("This may cause attachment processing to fail")
        
        # Check for HTML files
        html_files = list(config.processing_dir.rglob("*.html"))
        if not html_files:
            logger.warning(f"⚠️  No HTML files found in processing directory: {config.processing_dir}")
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
        
        logger.info("✅ Processing directory validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False


@click.group()
@click.option(
    '--processing-dir',
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd().parent / "gvoice-convert",
    help="Directory containing Google Voice export files (default: ../gvoice-convert)"
)
@click.option(
    '--max-workers',
    type=int,
    default=16,
    help="Maximum number of worker threads (default: 16)"
)
@click.option(
    '--chunk-size',
    type=int,
    default=1000,
    help="Chunk size for processing large files (default: 1000)"
)
@click.option(
    '--memory-threshold',
    type=int,
    default=10000,
    help="Memory threshold for switching to memory-efficient mode (default: 10000)"
)
@click.option(
    '--buffer-size',
    type=int,
    default=32768,
    help="Buffer size for file operations (default: 32768)"
)
@click.option(
    '--cache-size',
    type=int,
    default=50000,
    help="Cache size for frequently accessed data (default: 50000)"
)
@click.option(
    '--batch-size',
    type=int,
    default=1000,
    help="Batch size for processing operations (default: 1000)"
)
@click.option(
    '--enable-parallel-processing/--no-parallel-processing',
    default=True,
    help="Enable parallel processing (default: enabled)"
)
@click.option(
    '--enable-streaming-parsing/--no-streaming-parsing',
    default=True,
    help="Enable streaming parsing for large files (default: enabled)"
)
@click.option(
    '--enable-mmap-for-large-files/--no-mmap-for-large-files',
    default=True,
    help="Enable memory mapping for large files (default: enabled)"
)
@click.option(
    '--enable-performance-monitoring/--no-performance-monitoring',
    default=True,
    help="Enable performance monitoring (default: enabled)"
)
@click.option(
    '--enable-progress-logging/--no-progress-logging',
    default=True,
    help="Enable progress logging (default: enabled)"
)
@click.option(
    '--large-dataset/--no-large-dataset',
    default=True,
    help="Enable optimizations for datasets with 50,000+ messages (default: enabled)"
)
@click.option(
    '--enable-path-validation/--no-path-validation',
    default=True,
    help="Enable path validation (default: enabled)"
)
@click.option(
    '--enable-runtime-validation/--no-runtime-validation',
    default=True,
    help="Enable runtime validation (default: enabled)"
)
@click.option(
    '--validation-interval',
    type=int,
    default=1000,
    help="Validation interval for runtime checks (default: 1000)"
)
@click.option(
    '--strict-mode/--no-strict-mode',
    default=False,
    help="Enable strict mode for validation (default: disabled)"
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='INFO',
    help="Logging level (default: INFO)"
)
@click.option(
    '--log-filename',
    type=str,
    default='gvoice_converter.log',
    help="Log filename (default: gvoice_converter.log)"
)
@click.option(
    '--verbose/--no-verbose',
    default=False,
    help="Enable verbose logging (INFO level) (default: disabled)"
)
@click.option(
    '--debug/--no-debug',
    default=False,
    help="Enable debug logging (DEBUG level) (default: disabled)"
)
@click.option(
    '--debug-attachments/--no-debug-attachments',
    default=False,
    help="Enable detailed debugging for attachment matching (default: disabled)"
)
@click.option(
    '--debug-paths/--no-debug-paths',
    default=False,
    help="Enable detailed debugging for path resolution and validation (default: disabled)"
)
@click.option(
    '--test-mode/--no-test-mode',
    default=False,
    help="Enable testing mode with limited processing (default: disabled, 100 entries when enabled)"
)
@click.option(
    '--test-limit',
    type=int,
    default=100,
    help="Number of entries to process in test mode (default: 100)"
)
@click.option(
    '--full-run/--no-full-run',
    default=False,
    help="Disable test mode and process all entries (default: disabled)"
)
@click.option(
    '--include-service-codes/--no-include-service-codes',
    default=False,
    help="Include service codes and short codes in processing (default: disabled)"
)
@click.option(
    '--filter-numbers-without-aliases/--no-filter-numbers-without-aliases',
    default=False,
    help="Filter out phone numbers that don't have aliases (default: disabled)"
)
@click.option(
    '--filter-non-phone-numbers/--no-filter-non-phone-numbers',
    default=False,
    help="Filter out toll-free numbers and non-US numbers (default: disabled)"
)
@click.option(
    '--older-than',
    type=str,
    help="Filter out messages older than specified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
)
@click.option(
    '--newer-than',
    type=str,
    help="Filter out messages newer than specified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
)
@click.option(
    '--enable-phone-prompts/--no-enable-phone-prompts',
    default=False,
    help="Enable interactive phone number alias prompts (default: disabled)"
)
@click.option(
    '--skip-filtered-contacts/--no-skip-filtered-contacts',
    default=True,
    help="Skip processing filtered contacts by default (except in group messages) (default: enabled)"
)
@click.option(
    '--filter-groups-with-all-filtered/--no-filter-groups-with-all-filtered',
    default=True,
    help="Filter out group conversations where ALL participants are marked to filter (default: enabled)"
)
@click.option(
    '--phone-lookup-file',
    type=click.Path(path_type=Path),
    help="Path to phone lookup file (default: processing_dir/phone_lookup.txt)"
)
@click.option(
    '--preset',
    type=click.Choice(['default', 'test', 'production']),
    default='default',
    help="Configuration preset to use as base (default: default)"
)
@click.pass_context
def cli(ctx, **kwargs):
    """Google Voice SMS Takeout HTML Converter (New Configuration System)."""
    # Initialize with configuration from command line arguments
    ctx.ensure_object(dict)
    
    try:
        # Extract processing directory and preset
        processing_dir = kwargs.pop('processing_dir')
        preset = kwargs.pop('preset')
        
        # Create configuration using our new system
        config = ConfigurationBuilder.create_with_presets(processing_dir, preset)
        
        # Override with CLI arguments
        config_dict = config.to_dict()
        config_dict.update(kwargs)
        
        # Create final configuration
        final_config = ProcessingConfig.from_dict(config_dict)
        
        ctx.obj['config'] = final_config
        ctx.obj['patcher'] = None  # Will be set during conversion
        
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def convert(ctx):
    """Convert Google Voice export files to SMS backup format."""
    config = ctx.obj['config']
    logger = logging.getLogger(__name__)
    
    try:
        # Set up logging
        setup_logging(config)
        
        # Log configuration
        logger.info("=" * 60)
        logger.info("Starting Google Voice SMS Takeout XML Conversion")
        logger.info("=" * 60)
        logger.info(f"Processing directory: {config.processing_dir}")
        logger.info(f"Output format: {config.output_format}")
        logger.info(f"Test mode: {config.test_mode}")
        if config.test_mode:
            logger.info(f"Test limit: {config.test_limit}")
        
        # Validate and set up processing paths
        if not validate_and_setup(config):
            logger.error("Setup failed - cannot proceed with conversion")
            sys.exit(1)
        
        # Initialize processing paths BEFORE patching to avoid recursion
        logger.info("🔧 Initializing processing paths...")
        from sms import setup_processing_paths
        setup_processing_paths(
            config.processing_dir,
            enable_phone_prompts=config.enable_phone_prompts,
            buffer_size=config.buffer_size,
            batch_size=config.batch_size,
            cache_size=config.cache_size,
            large_dataset=config.large_dataset,
            phone_lookup_file=config.phone_lookup_file
        )
        logger.info("✅ Processing paths initialized successfully")
        
        # Patch SMS module with new configuration system
        patcher = patch_sms_module_with_config(config)
        ctx.obj['patcher'] = patcher
        
        # Run the main conversion
        logger.info("🚀 Starting conversion process...")
        from sms import main as sms_main
        from core.processing_context import create_processing_context
        
        # Create processing context
        context = create_processing_context(config)
        sms_main(config, context)
        
        # Clean up patching
        if patcher:
            logger.info("🔄 Cleaning up SMS module patches...")
            unpatch_sms_module(patcher)
            ctx.obj['patcher'] = None
        
        logger.info("✅ Conversion completed successfully")
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        
        # Clean up patching on error
        if ctx.obj.get('patcher'):
            try:
                unpatch_sms_module(ctx.obj['patcher'])
                ctx.obj['patcher'] = None
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup patches: {cleanup_error}")
        
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate configuration and processing directory."""
    config = ctx.obj['config']
    
    try:
        # Check for validation errors
        validation_errors = config.get_validation_errors()
        
        if not validation_errors:
            click.echo("🔍 Configuration Validation")
            click.echo("=" * 40)
            click.echo("✅ Configuration is valid")
            click.echo(f"Processing directory: {config.processing_dir}")
            click.echo(f"Output format: {config.output_format}")
            click.echo(f"Test mode: {config.test_mode}")
            
            # Validate processing directory
            click.echo("\n🔍 Processing Directory Validation")
            click.echo("=" * 40)
            if validate_and_setup(config):
                click.echo("✅ Processing directory structure is valid")
                # Check for required subdirectories and files
                calls_dir = config.processing_dir / "Calls"
                phones_file = config.processing_dir / "Phones.vcf"
                
                if calls_dir.exists():
                    click.echo("  - Calls/ subdirectory: Found")
                else:
                    click.echo("  - Calls/ subdirectory: Missing")
                
                if phones_file.exists():
                    click.echo("  - Phones.vcf file: Found")
                else:
                    click.echo("  - Phones.vcf file: Missing")
            else:
                click.echo("❌ Processing directory validation failed")
                click.echo(f"  Directory: {config.processing_dir}")
                click.echo("  Please ensure the directory contains Google Voice export files")
        else:
            click.echo("❌ Configuration validation errors:", err=True)
            for error in validation_errors:
                click.echo(f"  - {error}", err=True)
            raise click.Abort()
            
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def config_export(ctx):
    """Export current configuration to various formats."""
    config = ctx.obj['config']
    
    # Export to dictionary format
    config_dict = config.to_dict()
    
    click.echo("📋 Configuration Export")
    click.echo("=" * 40)
    click.echo("Configuration as dictionary:")
    for key, value in config_dict.items():
        click.echo(f"  {key}: {value}")


@cli.command()
@click.pass_context
def create_config(ctx):
    """Create a sample configuration file."""
    config = ctx.obj['config']
    
    # Create configuration file in JSON format
    config_dict = config.to_dict()
    config_file = Path("gvoice_config.json")
    
    if config_file.exists():
        if not click.confirm(f"File {config_file} already exists. Overwrite?"):
            return
    
    import json
    with open(config_file, 'w') as f:
        json.dump(config_dict, f, indent=2, default=str)
    
    click.echo(f"✅ Created configuration file: {config_file}")
    click.echo("You can now modify the values in this file and load them using --config-file option.")


@cli.command()
@click.option(
    '--config-file',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Configuration file to load (JSON format)"
)
@click.pass_context
def load_config(ctx, config_file):
    """Load configuration from a file."""
    if not config_file:
        click.echo("❌ No configuration file specified")
        return
    
    try:
        import json
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Create configuration from file
        config = ProcessingConfig.from_dict(config_data)
        ctx.obj['config'] = config
        
        click.echo(f"✅ Configuration loaded from: {config_file}")
        click.echo(f"Processing directory: {config.processing_dir}")
        click.echo(f"Output format: {config.output_format}")
        
    except Exception as e:
        click.echo(f"❌ Failed to load configuration: {e}")
        raise click.Abort()


@cli.command()
@click.pass_context
def show_config(ctx):
    """Show current configuration."""
    config = ctx.obj['config']
    
    click.echo("📋 Current Configuration")
    click.echo("=" * 40)
    
    # Show key configuration values
    click.echo(f"Processing directory: {config.processing_dir}")
    click.echo(f"Output directory: {config.output_dir}")
    click.echo(f"Output format: {config.output_format}")
    click.echo(f"Phone lookup file: {config.phone_lookup_file}")
    click.echo(f"Test mode: {config.test_mode}")
    if config.test_mode:
        click.echo(f"Test limit: {config.test_limit}")
    click.echo(f"Max workers: {config.max_workers}")
    click.echo(f"Chunk size: {config.chunk_size}")
    click.echo(f"Buffer size: {config.buffer_size}")
    click.echo(f"Cache size: {config.cache_size}")
    click.echo(f"Batch size: {config.batch_size}")
    click.echo(f"Phone prompts: {config.enable_phone_prompts}")
    click.echo(f"Strict mode: {config.strict_mode}")
    click.echo(f"Large dataset: {config.large_dataset}")


if __name__ == '__main__':
    cli()
