#!/usr/bin/env python3
"""
Google Voice SMS Takeout XML Converter - CLI Interface

This module provides a simple, manually defined CLI interface that ensures
predictable behavior for all options and proper conflict validation.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
import dateutil.parser

# Import our new configuration system
from core.unified_config import AppConfig

# Import the main conversion logic from sms.py
from sms import main as sms_main, setup_processing_paths, validate_processing_directory


def setup_logging(config: AppConfig) -> None:
    """Set up logging based on configuration."""
    # Determine log level
    if config.debug:
        log_level = logging.DEBUG
    elif config.verbose:
        log_level = logging.INFO
    else:
        log_level = getattr(logging, config.effective_log_level.upper())
    
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


def set_global_variables_for_compatibility(config: AppConfig) -> None:
    """Set global variables in sms.py for backward compatibility.
    
    This function sets the global variables that the legacy code expects,
    allowing us to use the new configuration system while maintaining
    compatibility with existing functions.
    """
    import sms
    
    # Set processing directory variables
    sms.PROCESSING_DIRECTORY = config.processing_dir
    sms.OUTPUT_DIRECTORY = config.get_output_directory()
    sms.LOG_FILENAME = str(config.get_log_file_path())
    
    # Set performance variables
    sms.MAX_WORKERS = config.max_workers
    sms.CHUNK_SIZE_OPTIMAL = config.chunk_size
    sms.MEMORY_EFFICIENT_THRESHOLD = config.memory_threshold
    sms.BUFFER_SIZE_OPTIMAL = config.buffer_size
    sms.CACHE_SIZE_OPTIMAL = config.cache_size
    sms.BATCH_SIZE_OPTIMAL = config.batch_size
    
    # Set feature flags
    sms.ENABLE_PARALLEL_PROCESSING = config.enable_parallel_processing
    sms.ENABLE_STREAMING_PARSING = config.enable_streaming_parsing
    sms.ENABLE_MMAP_FOR_LARGE_FILES = config.enable_mmap_for_large_files
    sms.ENABLE_PERFORMANCE_MONITORING = config.enable_performance_monitoring
    sms.ENABLE_PROGRESS_LOGGING = config.enable_progress_logging
    
    # Set validation flags
    sms.ENABLE_PATH_VALIDATION = config.enable_path_validation
    sms.ENABLE_RUNTIME_VALIDATION = config.enable_runtime_validation
    
    # Set logging variables
    sms.LOG_LEVEL = getattr(logging, config.effective_log_level.upper())
    sms.VERBOSE = config.verbose
    sms.DEBUG = config.debug
    sms.DEBUG_ATTACHMENTS = config.debug_attachments
    sms.DEBUG_PATHS = config.debug_paths
    
    # Set test mode variables
    sms.TEST_MODE = config.is_test_mode
    sms.TEST_LIMIT = config.effective_test_limit
    sms.FULL_RUN = config.full_run
    
    # Set filtering variables
    sms.INCLUDE_SERVICE_CODES = config.include_service_codes
    sms.FILTER_NUMBERS_WITHOUT_ALIASES = config.filter_numbers_without_aliases
    sms.FILTER_NON_PHONE_NUMBERS = config.filter_non_phone_numbers
    
    # Set date filter variables
    sms.DATE_FILTER_OLDER_THAN = dateutil.parser.parse(config.older_than) if config.older_than else None
    sms.DATE_FILTER_NEWER_THAN = dateutil.parser.parse(config.newer_than) if config.newer_than else None
    
    # Set phone prompts variable
    sms.ENABLE_PHONE_PROMPTS = config.phone_prompts
    
    # Set skip filtered contacts variable
    sms.SKIP_FILTERED_CONTACTS = config.skip_filtered_contacts
    
    # Set output format variable
    sms.OUTPUT_FORMAT = config.output_format
    
    # Set strict mode variable
    sms.STRICT_MODE = config.strict_mode
    
    # Set large dataset variable
    sms.LARGE_DATASET = config.large_dataset
    
    # Set batch processing variable (always enabled for now)
    sms.ENABLE_BATCH_PROCESSING = True
    
    # Log the global variable setup
    logger = logging.getLogger(__name__)
    logger.info("✅ Global variables set for backward compatibility")
    logger.info(f"  Processing directory: {sms.PROCESSING_DIRECTORY}")
    logger.info(f"  Output directory: {sms.OUTPUT_DIRECTORY}")
    logger.info(f"  Max workers: {sms.MAX_WORKERS}")
    logger.info(f"  Test mode: {sms.TEST_MODE}")
    if sms.TEST_MODE:
        logger.info(f"  Test limit: {sms.TEST_LIMIT}")


def validate_and_setup(config: AppConfig) -> bool:
    """Validate configuration and set up processing paths."""
    try:
        # Validate processing directory
        if not validate_processing_directory(config.processing_dir):
            return False
        
        # Set up processing paths
        setup_processing_paths(config.processing_dir)
        return True
        
    except Exception as e:
        logging.error(f"Setup failed: {e}")
        return False


@click.group()
@click.option(
    '--processing-dir',
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd().parent / "gvoice-convert",
    help="Directory containing Google Voice export files"
)
@click.option(
    '--output-format',
    type=click.Choice(['html', 'xml']),
    default='html',
    help="Output format for converted conversations"
)
@click.option(
    '--max-workers',
    type=int,
    default=16,
    help="Maximum number of worker threads"
)
@click.option(
    '--chunk-size',
    type=int,
    default=1000,
    help="Chunk size for processing large files"
)
@click.option(
    '--memory-threshold',
    type=int,
    default=10000,
    help="Memory threshold for switching to memory-efficient mode"
)
@click.option(
    '--buffer-size',
    type=int,
    default=32768,
    help="Buffer size for file operations"
)
@click.option(
    '--cache-size',
    type=int,
    default=50000,
    help="Cache size for frequently accessed data"
)
@click.option(
    '--batch-size',
    type=int,
    default=1000,
    help="Batch size for processing operations"
)
@click.option(
    '--enable-parallel-processing/--no-parallel-processing',
    default=True,
    help="Enable parallel processing"
)
@click.option(
    '--enable-streaming-parsing/--no-streaming-parsing',
    default=True,
    help="Enable streaming parsing for large files"
)
@click.option(
    '--enable-mmap-for-large-files/--no-mmap-for-large-files',
    default=True,
    help="Enable memory mapping for large files"
)
@click.option(
    '--enable-performance-monitoring/--no-performance-monitoring',
    default=True,
    help="Enable performance monitoring"
)
@click.option(
    '--enable-progress-logging/--no-progress-logging',
    default=True,
    help="Enable progress logging"
)
@click.option(
    '--large-dataset/--no-large-dataset',
    default=False,
    help="Enable optimizations for datasets with 50,000+ messages"
)
@click.option(
    '--enable-path-validation/--no-path-validation',
    default=True,
    help="Enable path validation"
)
@click.option(
    '--enable-runtime-validation/--no-runtime-validation',
    default=True,
    help="Enable runtime validation"
)
@click.option(
    '--validation-interval',
    type=int,
    default=1000,
    help="Validation interval for runtime checks"
)
@click.option(
    '--strict-mode/--no-strict-mode',
    default=False,
    help="Enable strict mode for validation"
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='INFO',
    help="Logging level"
)
@click.option(
    '--log-filename',
    type=str,
    default='gvoice_converter.log',
    help="Log filename"
)
@click.option(
    '--verbose/--no-verbose',
    default=False,
    help="Enable verbose logging (INFO level)"
)
@click.option(
    '--debug/--no-debug',
    default=False,
    help="Enable debug logging (DEBUG level)"
)
@click.option(
    '--debug-attachments/--no-debug-attachments',
    default=False,
    help="Enable detailed debugging for attachment matching"
)
@click.option(
    '--debug-paths/--no-debug-paths',
    default=False,
    help="Enable detailed debugging for path resolution and validation"
)
@click.option(
    '--test-mode/--no-test-mode',
    default=False,
    help="Enable testing mode with limited processing (default: 100 entries)"
)
@click.option(
    '--test-limit',
    type=int,
    default=100,
    help="Number of entries to process in test mode"
)
@click.option(
    '--full-run/--no-full-run',
    default=False,
    help="Disable test mode and process all entries"
)
@click.option(
    '--include-service-codes/--no-include-service-codes',
    default=False,
    help="Include service codes and short codes in processing"
)
@click.option(
    '--filter-numbers-without-aliases/--no-filter-numbers-without-aliases',
    default=False,
    help="Filter out phone numbers that don't have aliases"
)
@click.option(
    '--filter-non-phone-numbers/--no-filter-non-phone-numbers',
    default=False,
    help="Filter out toll-free numbers and non-US numbers"
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
    '--phone-prompts/--no-phone-prompts',
    default=False,
    help="Enable interactive phone number alias prompts"
)
@click.option(
    '--skip-filtered-contacts/--no-skip-filtered-contacts',
    default=True,
    help="Skip processing filtered contacts by default (except in group messages)"
)
@click.pass_context
def cli(ctx, **kwargs):
    """Google Voice SMS Takeout XML Converter."""
    # Initialize with configuration from command line arguments
    ctx.ensure_object(dict)
    try:
        ctx.obj['config'] = AppConfig(**kwargs)
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
        logger.info(f"Test mode: {config.is_test_mode}")
        if config.is_test_mode:
            logger.info(f"Test limit: {config.effective_test_limit}")
        
        # Validate and set up processing paths
        if not validate_and_setup(config):
            logger.error("Setup failed - cannot proceed with conversion")
            sys.exit(1)
        
        # Set global variables for backward compatibility
        set_global_variables_for_compatibility(config)
        
        # Run the main conversion
        logger.info("🚀 Starting conversion process...")
        sms_main()
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
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
            click.echo(f"Test mode: {config.is_test_mode}")
            
            # Validate processing directory
            click.echo("\n🔍 Processing Directory Validation")
            click.echo("=" * 40)
            if validate_processing_directory(config.processing_dir):
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
    
    # Export to .env format
    env_content = config.to_env_file()
    click.echo("📋 Configuration Export")
    click.echo("=" * 40)
    click.echo("Environment file (.env) format:")
    click.echo(env_content)


@cli.command()
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


if __name__ == '__main__':
    cli()
