# Google Voice SMS Converter - CLI Migration Guide

## Overview

This document describes the migration from the old `argparse`-based command-line interface in `sms.py` to the new modern `Click`-based CLI system in `cli.py`.

## What Changed

### Old System (`sms.py`)
- **Argument Parsing**: Manual `argparse` setup with ~30+ arguments
- **Configuration**: Global variables set from command line arguments
- **Entry Point**: Single `main()` function with complex argument processing
- **Maintenance**: Arguments and configuration scattered throughout the code

### New System (`cli.py`)
- **Argument Parsing**: Simple, manually defined Click options for predictable behavior
- **Configuration**: Unified configuration system with validation and conflict detection
- **Entry Point**: Modern Click CLI with subcommands and clear error messages
- **Maintenance**: Explicit option definitions ensure reliability and clarity

## New CLI Commands

### Main Commands

#### `convert`
Convert Google Voice export files to SMS backup format.
```bash
python3 cli.py convert
```

#### `validate`
Validate configuration and processing directory structure.
```bash
python3 cli.py validate
```

#### `config-export`
Export current configuration to various formats.
```bash
python3 cli.py config-export
```

#### `create-config`
Create a sample configuration file.
```bash
python3 cli.py create-config
```

### Configuration Options

The new CLI provides **32 configuration options** with explicit definitions for predictable behavior:

#### Processing Options
- `--processing-dir DIRECTORY` - Directory containing Google Voice export data
- `--output-format [html|xml]` - Output format for conversation files
- `--max-workers INTEGER` - Maximum number of parallel workers
- `--chunk-size INTEGER` - Chunk size for parallel processing

#### Performance Options
- `--buffer-size INTEGER` - File I/O buffer size in bytes
- `--cache-size INTEGER` - LRU cache size for performance optimization
- `--batch-size INTEGER` - Batch size for processing large datasets
- `--enable-parallel-processing` - Enable parallel processing
- `--enable-streaming-parsing` - Enable streaming file parsing
- `--enable-mmap-for-large-files` - Enable memory mapping for large files

#### Validation Options
- `--enable-path-validation` - Enable comprehensive path validation
- `--enable-runtime-validation` - Enable runtime validation
- `--strict-mode` - Enable strict parameter validation
- `--validation-interval INTEGER` - Runtime validation check interval

#### Logging Options
- `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]` - Set specific log level
- `--log-filename TEXT` - Custom log filename
- `--verbose` - Enable verbose logging
- `--debug` - Enable debug logging
- `--debug-attachments` - Enable attachment debugging
- `--debug-paths` - Enable path debugging

#### Test Mode Options
- `--test-mode` - Enable testing mode with limited processing
- `--test-limit INTEGER` - Number of entries to process in test mode
- `--full-run` - Disable test mode and process all entries

#### Filtering Options
- `--include-service-codes` - Include service codes and short codes
- `--filter-numbers-without-aliases` - Filter numbers without aliases
- `--filter-non-phone-numbers` - Filter toll-free and non-US numbers
- `--older-than TEXT` - Filter messages older than specified date
- `--newer-than TEXT` - Filter messages newer than specified date
- `--phone-prompts` - Enable interactive phone number alias prompts

## Conflict Validation

The new CLI includes intelligent conflict detection that prevents incompatible option combinations:

### Critical Conflicts (Hard Failures)
- `--full-run` + `--test-limit` - Cannot process all entries AND limit to N entries
- `--full-run` + `--test-mode` - Cannot process all entries AND enable test mode
- `--verbose` + `--debug` - Cannot set both INFO and DEBUG logging levels

### Error Messages
When conflicts are detected, the CLI provides clear error messages explaining:
- Why the options conflict
- What each option means
- How to fix the conflict

### Example
```bash
$ python3 cli.py --full-run --test-limit 50 validate
Configuration error: 1 validation error for AppConfig
  Value error, Conflicting options: --full-run and --test-limit cannot be used together.
  • --full-run means 'process all entries without test mode limitations'
  • --test-limit means 'limit processing to N entries in test mode'
  • These are mutually exclusive concepts
  • Use --full-run to process all entries, or use --test-limit without --full-run for test mode
```

## Migration Examples

### Old Command
```bash
python3 sms.py /path/to/gvoice/data --verbose --test-mode --test-limit 50 --output-format xml
```

### New Command
```bash
python3 cli.py --processing-dir /path/to/gvoice/data --verbose --test-mode --test-limit 50 --output-format xml convert
```

### Old Command
```bash
python3 sms.py --create-config
```

### New Command
```bash
python3 cli.py create-config
```

## Configuration Files

### Environment Variables
The new system automatically loads configuration from environment variables with `GVOICE_` prefix:

```bash
export GVOICE_PROCESSING_DIR=/path/to/gvoice/data
export GVOICE_MAX_WORKERS=8
export GVOICE_TEST_LIMIT=100
export GVOICE_OUTPUT_FORMAT=xml
```

### .env Files
Create a `.env` file in your project directory:

```bash
python3 cli.py create-config
```

This creates a `.env` file with all current configuration values that you can modify.

## Backward Compatibility

The new CLI maintains full backward compatibility with existing code:

1. **Global Variables**: All legacy global variables are automatically set from the new configuration
2. **Function Calls**: Existing functions continue to work unchanged
3. **Processing Logic**: The core conversion logic remains identical
4. **Output Format**: Same output files and structure

## Benefits of the New System

### For Users
- **Better Help**: `python3 cli.py --help` shows all options with descriptions
- **Configuration Files**: Easy to save and reuse configuration
- **Validation**: Automatic validation of configuration and paths
- **Subcommands**: Clear separation of different operations

### For Developers
- **Single Source of Truth**: All configuration defined in `AppConfig`
- **Type Safety**: Full Pydantic validation with helpful error messages
- **Automatic CLI Generation**: No need to manually maintain argument definitions
- **Environment Integration**: Automatic loading from environment variables
- **Testing**: Easy to test configuration scenarios

## Testing the Migration

### Basic Validation
```bash
python3 cli.py validate
```

### Test Conversion
```bash
python3 cli.py --test-limit 5 convert
```

### Export Configuration
```bash
python3 cli.py --max-workers 8 --test-limit 50 config-export
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install click pydantic-settings
   ```

2. **Configuration Errors**: Use `validate` subcommand to check configuration
   ```bash
   python3 cli.py validate
   ```

3. **Path Issues**: Verify processing directory structure
   ```bash
   python3 cli.py --debug-paths validate
   ```

### Debug Mode
Enable debug logging for detailed troubleshooting:
```bash
python3 cli.py --debug convert
```

## Future Enhancements

The new CLI system is designed for extensibility:

- **New Subcommands**: Easy to add new operations
- **Configuration Presets**: Predefined configurations for common use cases
- **Plugin System**: Support for third-party extensions
- **API Integration**: REST API based on the same configuration system

## Support

For issues or questions about the new CLI system:

1. Check the configuration validation: `python3 cli.py validate`
2. Enable debug mode: `python3 cli.py --debug validate`
3. Review the configuration export: `python3 cli.py config-export`
4. Check the logs for detailed error information

## Migration Checklist

- [ ] Install new dependencies (`click`, `pydantic-settings`)
- [ ] Test basic CLI functionality (`python3 cli.py --help`)
- [ ] Validate configuration (`python3 cli.py validate`)
- [ ] Test conversion with new CLI (`python3 cli.py --test-limit 5 convert`)
- [ ] Create configuration file (`python3 cli.py create-config`)
- [ ] Update scripts and automation to use new CLI
- [ ] Remove old `sms.py` entry point (optional)

## Conclusion

The new CLI system provides a modern, maintainable interface while preserving all existing functionality. The migration is designed to be seamless, with no changes required to existing processing logic or output formats.
