#!/usr/bin/env python3
"""
Google Voice SMS Takeout HTML Converter - CLI Interface

This module provides a CLI interface that integrates with the new configuration
architecture for processing Google Voice Takeout exports.
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
# Performance constants imported where needed

# Import the main conversion logic from sms.py - moved to avoid circular import


def setup_logging(config: ProcessingConfig) -> None:
    """
    Set up thread-safe logging based on configuration.

    Bug #13 FIX: Uses QueueHandler and QueueListener for thread-safe
    file logging that works correctly even with MAX_WORKERS > 1.
    """
    from utils.thread_safe_logging import setup_thread_safe_logging

    # Determine log level
    if config.debug:
        log_level = logging.DEBUG
    elif config.verbose:
        log_level = logging.INFO
    else:
        log_level = getattr(logging, config.log_level.upper())

    # Determine log file path
    log_file = None
    if hasattr(config, 'output_dir') and config.output_dir:
        # Place log file in output directory
        log_file = config.output_dir / config.log_filename
    elif hasattr(config, 'processing_dir') and config.processing_dir:
        # Fallback to processing directory
        log_file = config.processing_dir / config.log_filename
    else:
        # Last resort: current directory
        log_file = Path(config.log_filename)

    # Set up thread-safe logging with both console and file output
    # This uses QueueHandler to prevent thread safety issues
    setup_thread_safe_logging(
        log_level=log_level,
        log_file=log_file,
        console_logging=True,
        include_thread_name=True
    )

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("✅ Thread-safe logging initialized (Bug #13 FIXED)")
    logger.info(f"📝 Log level: {logging.getLevelName(log_level)}")
    logger.info(f"📁 Log file: {log_file}")
    logger.info("=" * 60)


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
# Performance options now hardcoded in shared_constants.py for optimal defaults
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
    help="Enable test mode to process a limited number of files (default: disabled, processes 100 files when enabled)."
)
@click.option(
    '--test-limit',
    type=int,
    default=100,
    help="Number of files to process in test mode (default: 100)."
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
    default=True,
    help="Filter out toll-free numbers and non-US numbers (default: enabled)"
)
@click.option(
    '--exclude-older-than',
    type=str,
    help="Exclude messages older than specified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). Messages before this date will be filtered out."
)
@click.option(
    '--exclude-newer-than',
    type=str,
    help="Exclude messages newer than specified date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). Messages after this date will be filtered out."
)
@click.option(
    '--include-date-range',
    type=str,
    help="Include only messages within specified date range (YYYY-MM-DD_YYYY-MM-DD). Format: start_date_end_date. Example: 2022-08-01_2025-06-01"
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
    '--include-call-only-conversations/--no-include-call-only-conversations',
    default=False,
    help="Include conversations that contain only call records. By default, conversations with only call logs (no SMS/MMS/voicemail text) are filtered out to focus on text-based communication (default: disabled - call-only conversations filtered out)"
)
@click.option(
    '--filter-commercial-conversations/--no-filter-commercial-conversations',
    default=False,
    help="Filter out commercial/spam conversations (those with only STOP/UNSUBSCRIBE responses and optional confirmation). This helps remove marketing messages and automated notifications (default: disabled)"
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
@click.option('--output', type=click.Path(), help='Output file for phone inventory (default: phone_inventory.json)')
@click.pass_context
def phone_discovery(ctx, output):
    """Discover and catalog phone numbers from HTML files."""
    try:
        config = ctx.obj['config']

        # Set up logging (Bug #15 fix)
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import PhoneDiscoveryStage
        
        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )
        
        # Register and execute phone discovery stage
        discovery_stage = PhoneDiscoveryStage()
        manager.register_stage(discovery_stage)
        
        click.echo("🔍 Starting phone number discovery...")
        results = manager.execute_pipeline(stages=["phone_discovery"], config=config)
        
        if results["phone_discovery"].success:
            metadata = results["phone_discovery"].metadata

            # Check if stage was skipped (Bug #14 fix)
            if metadata.get('skipped'):
                click.echo(f"✅ Discovery already completed (skipped)")
                click.echo(f"   ⏭️  Stage was previously run - use --force to re-run")
            else:
                click.echo(f"✅ Discovery completed successfully!")
                click.echo(f"   📊 Discovered: {metadata.get('discovered_count', 'N/A')} phone numbers")
                click.echo(f"   ❓ Unknown: {metadata.get('unknown_count', 'N/A')} numbers")
                click.echo(f"   ✓ Known: {metadata.get('known_count', 'N/A')} numbers")
                click.echo(f"   📁 Files processed: {metadata.get('files_processed', 'N/A')}")

            if output:
                # Copy output to specified location
                import shutil
                src = config.processing_dir / "conversations" / "phone_inventory.json"
                if src.exists():
                    shutil.copy2(src, output)
                    click.echo(f"   💾 Output saved to: {output}")
                else:
                    click.echo(f"   ⚠️  Output file not found: {src}")
        else:
            click.echo("❌ Phone discovery failed:")
            for error in results["phone_discovery"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Phone discovery failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.option('--input', type=click.Path(exists=True), help='Phone inventory file (default: phone_inventory.json)')
@click.option('--provider', type=click.Choice(['ipqualityscore', 'truecaller', 'manual']), 
              default='manual', help='Lookup provider to use')
@click.option('--api-key', help='API key for the lookup provider')
@click.option('--export-unknown', type=click.Path(), help='Export unknown numbers to CSV')
@click.pass_context
def phone_lookup(ctx, input, provider, api_key, export_unknown):
    """Perform phone number lookup and enrichment."""
    try:
        config = ctx.obj['config']

        # Set up logging (Bug #15 fix)
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import PhoneDiscoveryStage, PhoneLookupStage
        
        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )
        
        # Register stages
        discovery_stage = PhoneDiscoveryStage()
        lookup_stage = PhoneLookupStage(api_provider=provider, api_key=api_key)
        manager.register_stages([discovery_stage, lookup_stage])
        
        click.echo(f"📞 Starting phone lookup using provider: {provider}")
        
        if provider != 'manual' and not api_key:
            click.echo("⚠️  No API key provided - switching to manual mode")
            lookup_stage = PhoneLookupStage(api_provider='manual')
            manager.stages['phone_lookup'] = lookup_stage
        
        # Execute pipeline
        results = manager.execute_pipeline(config=config)
        
        if results["phone_lookup"].success:
            metadata = results["phone_lookup"].metadata
            click.echo(f"✅ Phone lookup completed successfully!")
            click.echo(f"   📊 Numbers processed: {metadata['numbers_processed']}")
            click.echo(f"   🎯 Success rate: {metadata['lookup_success_rate']:.1%}")
            click.echo(f"   🔧 Provider: {metadata['api_provider']}")
            
            if provider == 'manual':
                click.echo(f"   📝 Export unknown numbers to CSV for manual lookup")
                csv_path = config.processing_dir / "conversations" / "unknown_numbers.csv"
                if csv_path.exists():
                    click.echo(f"   💾 CSV file: {csv_path}")
                    
            if export_unknown:
                # Copy CSV to specified location
                import shutil
                src = config.processing_dir / "conversations" / "unknown_numbers.csv"
                if src.exists():
                    shutil.copy2(src, export_unknown)
                    click.echo(f"   💾 Unknown numbers exported to: {export_unknown}")
        else:
            click.echo("❌ Phone lookup failed:")
            for error in results["phone_lookup"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Phone lookup failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.option('--api', type=click.Choice(['ipqualityscore', 'truecaller']), 
              help='API provider for phone lookup')
@click.option('--api-key', help='API key for the lookup provider')
@click.pass_context
def phone_pipeline(ctx, api, api_key):
    """Run complete phone discovery and lookup pipeline."""
    try:
        config = ctx.obj['config']

        # Set up logging (Bug #15 fix)
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import PhoneDiscoveryStage, PhoneLookupStage
        
        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )
        
        # Register stages
        discovery_stage = PhoneDiscoveryStage()
        
        if api and api_key:
            lookup_stage = PhoneLookupStage(api_provider=api, api_key=api_key)
        else:
            lookup_stage = PhoneLookupStage(api_provider='manual')
            
        manager.register_stages([discovery_stage, lookup_stage])
        
        click.echo("🚀 Starting complete phone processing pipeline...")
        
        # Execute full pipeline
        results = manager.execute_pipeline(config=config)
        
        # Report results
        discovery_result = results.get("phone_discovery")
        lookup_result = results.get("phone_lookup")
        
        if discovery_result and discovery_result.success:
            metadata = discovery_result.metadata
            click.echo(f"✅ Phone discovery completed!")
            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📊 Discovered: {metadata.get('discovered_count', 'N/A')} phone numbers")
                click.echo(f"   ❓ Unknown: {metadata.get('unknown_count', 'N/A')} numbers")
        else:
            click.echo("❌ Phone discovery failed")
            
        if lookup_result and lookup_result.success:
            metadata = lookup_result.metadata
            click.echo(f"✅ Phone lookup completed!")
            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📊 Numbers processed: {metadata.get('numbers_processed', 'N/A')}")
                click.echo(f"   🔧 Provider: {metadata.get('api_provider', 'N/A')}")
        else:
            click.echo("❌ Phone lookup failed")
            
        # Show overall status
        if all(r.success for r in results.values()):
            click.echo("🎉 Phone processing pipeline completed successfully!")
        else:
            click.echo("⚠️  Phone processing pipeline completed with errors")
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Phone pipeline failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.option('--output', type=click.Path(), help='Output file for file inventory (default: file_inventory.json)')
@click.pass_context
def file_discovery(ctx, output):
    """Discover and catalog HTML files in the processing directory."""
    try:
        config = ctx.obj['config']

        # Set up logging (Bug #15 fix)
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import FileDiscoveryStage
        
        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )
        
        # Register and execute file discovery stage
        discovery_stage = FileDiscoveryStage()
        manager.register_stage(discovery_stage)
        
        click.echo("📁 Starting file discovery...")
        results = manager.execute_pipeline(stages=["file_discovery"], config=config)
        
        if results["file_discovery"].success:
            metadata = results["file_discovery"].metadata

            # Check if stage was skipped (Bug #14 fix)
            if metadata.get('skipped'):
                click.echo(f"✅ File discovery already completed (skipped)")
                click.echo(f"   ⏭️  Stage was previously run - use --force to re-run")
            else:
                click.echo(f"✅ File discovery completed successfully!")
                click.echo(f"   📊 Total files: {metadata.get('total_files', 'N/A')}")
                click.echo(f"   📁 File types: {metadata.get('type_counts', 'N/A')}")
                click.echo(f"   💾 Total size: {metadata.get('total_size_mb', 'N/A')} MB")
                click.echo(f"   🔍 Largest file: {metadata.get('largest_file_mb', 'N/A')} MB")

            if output:
                # Copy output to specified location
                import shutil
                src = config.processing_dir / "conversations" / "file_inventory.json"
                if src.exists():
                    shutil.copy2(src, output)
                    click.echo(f"   💾 Output saved to: {output}")
                else:
                    click.echo(f"   ⚠️  Output file not found: {src}")
        else:
            click.echo("❌ File discovery failed:")
            for error in results["file_discovery"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"❌ File discovery failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.option('--max-files', type=int, default=1000, help='Maximum files to process per batch')
@click.option('--output', type=click.Path(), help='Output file for extracted content (default: extracted_content.json)')
@click.pass_context
def content_extraction(ctx, max_files, output):
    """Extract structured content from HTML files."""
    try:
        config = ctx.obj['config']

        # Set up logging (Bug #15 fix)
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import FileDiscoveryStage, ContentExtractionStage
        
        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )
        
        # Register stages
        discovery_stage = FileDiscoveryStage()
        extraction_stage = ContentExtractionStage(max_files_per_batch=max_files)
        manager.register_stages([discovery_stage, extraction_stage])
        
        click.echo(f"🔍 Starting content extraction (max {max_files} files)...")
        
        # Execute pipeline
        results = manager.execute_pipeline(config=config)
        
        if results["content_extraction"].success:
            metadata = results["content_extraction"].metadata
            click.echo(f"✅ Content extraction completed successfully!")
            click.echo(f"   📊 Files processed: {metadata['files_processed']}")
            click.echo(f"   💬 Conversations: {metadata['conversations_extracted']}")
            click.echo(f"   📝 Total messages: {metadata['total_messages']}")
            click.echo(f"   👥 Participants: {metadata['total_participants']}")
            
            if metadata['extraction_errors'] > 0:
                click.echo(f"   ⚠️  Extraction errors: {metadata['extraction_errors']}")
                
            if output:
                # Copy output to specified location
                import shutil
                src = config.processing_dir / "conversations" / "extracted_content.json"
                shutil.copy2(src, output)
                click.echo(f"   💾 Output saved to: {output}")
        else:
            click.echo("❌ Content extraction failed:")
            for error in results["content_extraction"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Content extraction failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.option('--max-files', type=int, default=1000, help='Maximum files to process per batch')
@click.pass_context
def file_pipeline(ctx, max_files):
    """Run complete file discovery and content extraction pipeline."""
    try:
        config = ctx.obj['config']

        # Set up logging (Bug #15 fix)
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import FileDiscoveryStage, ContentExtractionStage
        
        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )
        
        # Register stages
        discovery_stage = FileDiscoveryStage()
        extraction_stage = ContentExtractionStage(max_files_per_batch=max_files)
        manager.register_stages([discovery_stage, extraction_stage])
        
        click.echo("🚀 Starting complete file processing pipeline...")
        
        # Execute full pipeline
        results = manager.execute_pipeline(config=config)
        
        # Report results
        discovery_result = results.get("file_discovery")
        extraction_result = results.get("content_extraction")
        
        if discovery_result and discovery_result.success:
            metadata = discovery_result.metadata
            click.echo(f"✅ File discovery completed!")
            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📊 Total files: {metadata.get('total_files', 'N/A')}")
                click.echo(f"   📁 File types: {metadata.get('type_counts', 'N/A')}")
        else:
            click.echo("❌ File discovery failed")
            
        if extraction_result and extraction_result.success:
            metadata = extraction_result.metadata
            click.echo(f"✅ Content extraction completed!")
            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   💬 Conversations: {metadata.get('conversations_extracted', 'N/A')}")
                click.echo(f"   📝 Messages: {metadata.get('total_messages', 'N/A')}")
        else:
            click.echo("❌ Content extraction failed")
            
        # Show overall status
        if all(r.success for r in results.values()):
            click.echo("🎉 File processing pipeline completed successfully!")
        else:
            click.echo("⚠️  File processing pipeline completed with errors")
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"❌ File pipeline failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.pass_context
def attachment_mapping(ctx):
    """Build attachment mapping as a pipeline stage."""
    try:
        config = ctx.obj['config']

        # Set up logging
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import AttachmentMappingStage

        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )

        # Register stage
        stage = AttachmentMappingStage()
        manager.register_stage(stage)

        click.echo("🔍 Starting attachment mapping...")

        # Execute stage
        results = manager.execute_pipeline(config=config)

        if results["attachment_mapping"].success:
            metadata = results["attachment_mapping"].metadata
            click.echo(f"✅ Attachment mapping completed!")
            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📊 Total mappings: {metadata['total_mappings']}")
                click.echo(f"   💾 Output: {metadata['output_file']}")
        else:
            click.echo("❌ Attachment mapping failed:")
            for error in results["attachment_mapping"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)

    except Exception as e:
        click.echo(f"❌ Attachment mapping failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.pass_context
def attachment_copying(ctx):
    """Copy attachments to output directory (requires attachment-mapping)."""
    try:
        config = ctx.obj['config']

        # Set up logging
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import AttachmentMappingStage, AttachmentCopyingStage

        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )

        # Register both stages (attachment_copying depends on attachment_mapping)
        manager.register_stage(AttachmentMappingStage())
        manager.register_stage(AttachmentCopyingStage())

        click.echo("📋 Starting attachment copying pipeline...")

        # Execute pipeline (will auto-skip attachment_mapping if already done)
        results = manager.execute_pipeline(config=config)

        # Check attachment_copying result
        if results["attachment_copying"].success:
            metadata = results["attachment_copying"].metadata
            click.echo(f"✅ Attachment copying completed!")
            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📋 Copied: {metadata['total_copied']}")
                click.echo(f"   ⏭️  Skipped: {metadata['total_skipped']}")
                click.echo(f"   ⚠️  Errors: {metadata['total_errors']}")
                click.echo(f"   💾 Output: {metadata['output_dir']}")

            # Show errors if any
            if results["attachment_copying"].errors:
                click.echo(f"\n⚠️  Warnings:")
                for error in results["attachment_copying"].errors[:5]:  # Show first 5
                    click.echo(f"   {error}")
                if len(results["attachment_copying"].errors) > 5:
                    click.echo(f"   ... and {len(results['attachment_copying'].errors) - 5} more")
        else:
            click.echo("❌ Attachment copying failed:")
            for error in results["attachment_copying"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)

    except Exception as e:
        click.echo(f"❌ Attachment copying failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.pass_context
def html_generation(ctx):
    """Generate HTML conversations from processed files (requires attachment stages)."""
    try:
        config = ctx.obj['config']

        # Set up logging
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import (
            AttachmentMappingStage,
            AttachmentCopyingStage,
            HtmlGenerationStage
        )

        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )

        # Register all three stages (html_generation depends on both attachment stages)
        manager.register_stage(AttachmentMappingStage())
        manager.register_stage(AttachmentCopyingStage())
        manager.register_stage(HtmlGenerationStage())

        click.echo("📝 Starting HTML generation pipeline...")

        # Execute pipeline (will auto-skip completed stages)
        results = manager.execute_pipeline(config=config)

        # Check html_generation result
        if results["html_generation"].success:
            metadata = results["html_generation"].metadata
            click.echo(f"✅ HTML generation completed!")

            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📊 SMS: {metadata.get('total_sms', 0)}")
                click.echo(f"   🖼️  Images: {metadata.get('total_img', 0)}")
                click.echo(f"   📇 vCards: {metadata.get('total_vcf', 0)}")
                click.echo(f"   📞 Calls: {metadata.get('total_calls', 0)}")
                click.echo(f"   🎙️  Voicemails: {metadata.get('total_voicemails', 0)}")
                click.echo(f"   📋 Files processed this run: {metadata.get('files_processed', 0)}")
                click.echo(f"   ⏭️  Files skipped: {metadata.get('files_skipped', 0)}")
                click.echo(f"   💾 Output: {config.processing_dir / 'conversations'}")

            # Show errors if any
            if results["html_generation"].errors:
                click.echo(f"\n⚠️  Errors:")
                for error in results["html_generation"].errors[:5]:
                    click.echo(f"   {error}")
                if len(results["html_generation"].errors) > 5:
                    click.echo(f"   ... and {len(results['html_generation'].errors) - 5} more")
        else:
            click.echo("❌ HTML generation failed:")
            for error in results["html_generation"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)

    except Exception as e:
        click.echo(f"❌ HTML generation failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@cli.command()
@click.pass_context
def index_generation(ctx):
    """Generate index.html from conversation files (requires html-generation stage)."""
    try:
        config = ctx.obj['config']

        # Set up logging
        setup_logging(config)

        # Import pipeline components
        from core.pipeline import PipelineManager
        from core.pipeline.stages import (
            AttachmentMappingStage,
            AttachmentCopyingStage,
            HtmlGenerationStage,
            IndexGenerationStage
        )

        # Create pipeline manager
        manager = PipelineManager(
            processing_dir=config.processing_dir,
            output_dir=config.processing_dir / "conversations"
        )

        # Register all stages (index_generation depends on html_generation)
        manager.register_stage(AttachmentMappingStage())
        manager.register_stage(AttachmentCopyingStage())
        manager.register_stage(HtmlGenerationStage())
        manager.register_stage(IndexGenerationStage())

        click.echo("📝 Starting index generation pipeline...")

        # Execute pipeline (will auto-skip completed stages)
        results = manager.execute_pipeline(config=config)

        # Check index_generation result
        if results["index_generation"].success:
            metadata = results["index_generation"].metadata
            click.echo(f"✅ Index generation completed!")

            if metadata.get('skipped'):
                click.echo(f"   ⏭️  Stage was skipped (already completed)")
            else:
                click.echo(f"   📊 Total conversations: {metadata.get('total_conversations', 0)}")
                click.echo(f"   📋 Files processed: {metadata.get('total_conversations', 0)}")
                click.echo(f"   ⏭️  Files skipped: {metadata.get('files_skipped', 0)}")
                click.echo(f"   💾 Output: {config.processing_dir / 'conversations' / 'index.html'}")

            # Show errors if any
            if results["index_generation"].errors:
                click.echo(f"\n⚠️  Errors:")
                for error in results["index_generation"].errors[:5]:
                    click.echo(f"   {error}")
                if len(results["index_generation"].errors) > 5:
                    click.echo(f"   ... and {len(results['index_generation'].errors) - 5} more")
        else:
            click.echo("❌ Index generation failed:")
            for error in results["index_generation"].errors:
                click.echo(f"   {error}")
            ctx.exit(1)

    except Exception as e:
        click.echo(f"❌ Index generation failed: {e}")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        ctx.exit(1)


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
        logger.info("Starting Google Voice SMS Takeout HTML Conversion")
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
            # buffer_size is now hardcoded in shared_constants.py
            # batch_size is now hardcoded in shared_constants.py
            # cache_size is now hardcoded in shared_constants.py
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
    from core.shared_constants import BUFFER_SIZE_OPTIMAL, BATCH_SIZE_OPTIMAL
    click.echo(f"Buffer size: {BUFFER_SIZE_OPTIMAL} (hardcoded)")
    click.echo(f"Cache size: N/A (removed during performance optimization)")
    click.echo(f"Batch size: {BATCH_SIZE_OPTIMAL} (hardcoded)")
    click.echo(f"Phone prompts: {config.enable_phone_prompts}")
    click.echo(f"Strict mode: {config.strict_mode}")
    click.echo(f"Large dataset: {config.large_dataset}")


@cli.command()
@click.option('--attachment', is_flag=True, help='Clear attachment cache (.cache/)')
@click.option('--pipeline', is_flag=True, help='Clear pipeline state (pipeline_state/)')
@click.option('--all', 'clear_all', is_flag=True, help='Clear both caches')
@click.pass_context
def clear_cache(ctx, attachment, pipeline, clear_all):
    """Clear caches to force fresh processing.

    This project uses multiple caches:

    1. Python Bytecode Cache (*.pyc, __pycache__/) - Ensures latest code is used

    2. Attachment Cache (.cache/) - Speeds up attachment mapping

    3. Pipeline State (pipeline_state/) - Tracks completed pipeline stages

    4. HTML Processing State (html_processing_state.json) - Tracks processed HTML files

    Use --all to clear all caches (recommended for clean regeneration), or specify individual caches.
    
    Note: Python bytecode cache is only cleared with --all to ensure fresh code execution.
    """
    import shutil

    config = ctx.obj['config']
    processing_dir = config.processing_dir

    cleared = []

    # Clear Python bytecode cache first (when clearing all)
    if clear_all:
        import subprocess
        try:
            # Clear .pyc files and __pycache__ directories in project
            project_root = Path(__file__).parent
            pyc_count = 0
            pycache_count = 0
            
            # Remove .pyc files
            for pyc_file in project_root.rglob("*.pyc"):
                try:
                    pyc_file.unlink()
                    pyc_count += 1
                except Exception:
                    pass
            
            # Remove __pycache__ directories
            for pycache_dir in project_root.rglob("__pycache__"):
                try:
                    shutil.rmtree(pycache_dir)
                    pycache_count += 1
                except Exception:
                    pass
            
            if pyc_count > 0 or pycache_count > 0:
                cleared.append(f"Python bytecode cache ({pyc_count} .pyc files, {pycache_count} __pycache__ dirs)")
                click.echo(f"✅ Cleared Python bytecode: {pyc_count} .pyc files, {pycache_count} __pycache__ directories")
            else:
                click.echo("ℹ️  No Python bytecode cache found")
        except Exception as e:
            click.echo(f"⚠️  Failed to clear Python bytecode cache: {e}")
    
    # Clear attachment cache
    if attachment or clear_all:
        cache_dir = processing_dir / ".cache"
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                cleared.append("Attachment cache (.cache/)")
                click.echo(f"✅ Cleared: {cache_dir}")
            except Exception as e:
                click.echo(f"❌ Failed to clear attachment cache: {e}")
        else:
            click.echo(f"ℹ️  Attachment cache does not exist: {cache_dir}")

    # Clear pipeline state
    if pipeline or clear_all:
        state_dir = processing_dir / "conversations" / "pipeline_state"
        if state_dir.exists():
            try:
                shutil.rmtree(state_dir)
                cleared.append("Pipeline state (pipeline_state/)")
                click.echo(f"✅ Cleared: {state_dir}")
            except Exception as e:
                click.echo(f"❌ Failed to clear pipeline state: {e}")
        else:
            click.echo(f"ℹ️  Pipeline state does not exist: {state_dir}")
        
        # Also clear html_processing_state.json
        html_state_file = processing_dir / "conversations" / "html_processing_state.json"
        if html_state_file.exists():
            try:
                html_state_file.unlink()
                cleared.append("HTML processing state (html_processing_state.json)")
                click.echo(f"✅ Cleared: {html_state_file}")
            except Exception as e:
                click.echo(f"❌ Failed to clear HTML processing state: {e}")
        else:
            click.echo(f"ℹ️  HTML processing state does not exist: {html_state_file}")

    # Show summary
    if not (attachment or pipeline or clear_all):
        click.echo("❌ No cache specified. Use --attachment, --pipeline, or --all")
        click.echo("\nRun 'python cli.py clear-cache --help' for more information")
        ctx.exit(1)
    elif cleared:
        click.echo(f"\n🎉 Cleared {len(cleared)} cache(s): {', '.join(cleared)}")
        click.echo("\nNext run will rebuild from scratch.")
    else:
        click.echo("\nℹ️  No caches found to clear.")


if __name__ == '__main__':
    cli()
