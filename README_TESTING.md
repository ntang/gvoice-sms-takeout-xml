# SMS Module Testing Guide

## Overview

This document describes how to run tests for the SMS module. The testing infrastructure has been refactored to eliminate redundancy and improve maintainability.

## 🆕 New Unified Testing Approach

**Recommended**: Use `test_sms_unified.py` for all testing needs.

### Quick Start

```bash
# Basic tests only (fastest)
python test_sms_unified.py --basic

# Full test suite
python test_sms_unified.py --full

# Integration tests only
python test_sms_unified.py --integration

# See all options
python test_sms_unified.py --help
```

### Test Suite Options

| Option | Description | Test Count | Speed |
|--------|-------------|------------|-------|
| `--basic` | Core functionality tests only | ~36 tests | ⚡ Fastest |
| `--advanced` | Basic + Advanced tests | ~40 tests | 🚀 Fast |
| `--full` | Complete test suite (no integration) | ~40 tests | 🚀 Fast |
| `--integration` | Integration tests only | ~8 tests | 🐌 Slow |

### Performance Options

```bash
# Set test limit for faster execution (default: 100)
python test_sms_unified.py --basic --limit 50

# Verbose output
python test_sms_unified.py --full -v

# Custom traceback style
python test_sms_unified.py --basic --tb short
```

### Examples

```bash
# Quick development testing
python test_sms_unified.py --basic --limit 25

# Full validation before release
python test_sms_unified.py --full --limit 200

# Debug integration issues
python test_sms_unified.py --integration -v
```

## 🚫 Deprecated Test Files

The following test files are deprecated and will be removed in a future version:

- `test_sms.py` - Replaced by unified test suite
- `test_sms_basic.py` - Replaced by unified test suite

These files still work for backward compatibility but will show deprecation warnings and redirect to the unified approach.

## Test Structure

### TestSMSBasic
Core functionality tests that don't require external dependencies:
- Constants and configuration validation
- XML escaping and formatting
- File processing utilities
- Performance monitoring functions
- Template validation

### TestSMSAdvanced
Advanced functionality tests:
- Message type detection
- Text extraction
- Timestamp processing
- Phone number formatting

### TestSMSIntegration
Integration tests that test the full system:
- Processing path setup
- Conversation management
- Phone lookup management
- Attachment processing
- HTML processing
- MMS processing

## Performance Considerations

### Test Limits
- **Default limit**: 100 objects (good balance of speed vs coverage)
- **Development**: Use 25-50 for quick feedback
- **CI/CD**: Use 100-200 for comprehensive validation
- **Production**: Use 500+ for thorough testing

### Test Suite Selection
- **Daily development**: `--basic --limit 25`
- **Feature completion**: `--advanced --limit 100`
- **Release preparation**: `--full --limit 200`
- **Bug investigation**: `--integration -v`

## Running Tests with pytest

The unified test file can also be run with pytest:

```bash
# Run all tests
pytest test_sms_unified.py -v

# Run specific test class
pytest test_sms_unified.py::TestSMSBasic -v

# Run specific test method
pytest test_sms_unified.py::TestSMSBasic::test_escape_xml -v
```

## Test Configuration

### Environment Setup
Tests automatically:
- Create temporary directories for test files
- Suppress logging during test execution
- Clean up after each test
- Set appropriate test limits

### Mock Objects
Tests use comprehensive mocking for:
- File system operations
- BeautifulSoup objects
- Phone number objects
- External dependencies

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're in the correct directory
2. **Test failures**: Check that `sms.py` is working correctly
3. **Performance issues**: Reduce test limits with `--limit N`
4. **Integration test failures**: May indicate system configuration issues

### Debug Mode

```bash
# Verbose output with full tracebacks
python test_sms_unified.py --full -v --tb long

# Run specific test suite with debugging
python test_sms_unified.py --integration -v
```

## Contributing

### Adding New Tests

1. **Basic tests**: Add to `TestSMSBasic` class
2. **Advanced tests**: Add to `TestSMSAdvanced` class  
3. **Integration tests**: Add to `TestSMSIntegration` class

### Test Guidelines

- Each test should be independent
- Use descriptive test method names
- Include comprehensive assertions
- Clean up resources in `tearDown`
- Use appropriate mocking for external dependencies

### Running Your New Tests

```bash
# Test specific class
python test_sms_unified.py --basic --limit 100

# Test with pytest for better debugging
pytest test_sms_unified.py::TestSMSBasic::test_your_new_test -v
```

## Migration from Old Test Files

If you were using the old test files:

```bash
# Old way
python test_sms.py
python test_sms_basic.py

# New way
python test_sms_unified.py --full
python test_sms_unified.py --basic
```

The old files will continue to work but will show deprecation warnings and redirect to the unified approach.

## Performance Benchmarks

Typical execution times on modern hardware:

| Test Suite | Limit | Time | Memory |
|------------|-------|------|--------|
| Basic | 25 | ~0.01s | Low |
| Basic | 100 | ~0.01s | Low |
| Advanced | 100 | ~0.01s | Low |
| Full | 100 | ~0.01s | Low |
| Integration | 50 | ~0.5s | Medium |
| Full + Integration | 200 | ~1.0s | Medium |

## Conclusion

The unified testing approach provides:
- ✅ **No redundancy** - Tests defined once
- ✅ **Better performance** - Configurable test limits
- ✅ **Easier maintenance** - Single source of truth
- ✅ **Flexible execution** - Choose test scope and performance
- ✅ **Backward compatibility** - Old test files still work

Use `python test_sms_unified.py --help` to see all available options and start testing efficiently!
