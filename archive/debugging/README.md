# Debugging Test Files

This directory contains test files used during the debugging of the pydantic-settings integration issue.

## Files

- **`test_pydantic.py`** - Tests comparing regular Pydantic vs pydantic-settings behavior
- **`test_path_fields.py`** - Tests for Path field behavior with different default types
- **`test_minimal.py`** - Minimal configurations to isolate the alias field issue
- **`demo_cli.py`** - Demo script for testing Click CLI integration with unified configuration

## Issue Resolved

The root cause was identified as the `alias="processing_directory"` field in the `AppConfig.processing_dir` definition. When using aliases with pydantic-settings, constructor arguments were being ignored and default values were always used.

## Solution Applied

Removed the `alias="processing_directory"` from the `processing_dir` field in `core/unified_config.py`. This resolved the issue and allowed the configuration system to work correctly with both default values and custom constructor arguments.

## Lessons Learned

1. **Alias fields in pydantic-settings can interfere with constructor argument processing**
2. **Path fields work correctly with regular `default` values (not `default_factory`)**
3. **Field validators don't cause the constructor argument issue**
4. **The `SettingsConfigDict` style works correctly when aliases are not used**
