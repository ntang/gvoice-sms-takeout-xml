# Testing Framework for SMS.py

This document describes the comprehensive testing framework built for `sms.py` to ensure code quality and validate future changes.

## 🎯 Overview

The testing framework provides:
- **Unit Tests**: Individual function testing with mocked dependencies
- **Integration Tests**: End-to-end workflow testing
- **Error Handling Tests**: Validation of exception handling
- **Edge Case Tests**: Boundary condition testing
- **Performance Tests**: Validation of optimizations

## 📁 Test Files

### Core Test Files
- **`test_sms_unified.py`** - Main unified test suite with all test cases
- **`run_tests.py`** - Test runner script with multiple execution modes
- **`test_requirements.txt`** - Dependencies for advanced testing features

### Test Structure
```
test_sms_unified.py
├── TestSMSBasic (Unit Tests)
│   ├── Configuration & Constants
│   ├── Core Functions
│   ├── XML Generation
│   ├── File Processing
│   ├── Error Handling
│   └── Performance Optimizations
├── TestSMSAdvanced (Advanced Tests)
│   ├── Message Processing
│   ├── Phone Number Handling
│   └── Edge Cases
└── TestSMSIntegration (Integration Tests)
    ├── Full Workflow Testing
    ├── Attachment Processing
    └── Filename-based Extraction
```

## 🚀 Running Tests

### Quick Start
```bash
# Run basic tests (no additional dependencies)
python3 run_tests.py

# Run quick validation only
python3 run_tests.py --quick

# Run with pytest (if installed)
python3 run_tests.py --pytest

# Run with coverage reporting
python3 run_tests.py --coverage
```

### Manual Execution
```bash
# Using unittest directly
python3 -m unittest test_sms_unified -v

# Using pytest (if installed)
python3 -m pytest test_sms_unified.py -v

# Using pytest with coverage
python3 -m pytest test_sms_unified.py --cov=sms --cov-report=html
```

## 📋 Test Categories

### 1. Configuration & Constants
- **`test_validate_configuration`**: Ensures all required constants are defined
- **`test_conversion_stats_dataclass`**: Validates data structure integrity

### 2. Core Functions
- **`test_escape_xml`**: XML character escaping functionality
- **`test_format_elapsed_time`**: Time formatting with timedelta
- **`test_normalize_filename`**: Filename sanitization and truncation
- **`test_custom_filename_sort`**: Custom sorting algorithm

### 3. XML Generation
- **`test_build_attachment_xml_part`**: Attachment XML part creation
- **`test_build_participants_xml`**: Participant XML generation
- **`test_build_mms_xml`**: Complete MMS XML structure

### 4. File Processing
- **`test_parse_html_file`**: HTML parsing with error handling
- **`test_count_attachments_in_file`**: Attachment counting logic
- **`test_src_to_filename_mapping`**: Source-to-filename mapping

### 5. Phone Number Handling
- **`test_format_number`**: Phone number formatting to E164
- **`test_extract_own_phone_number`**: Own number extraction
- **`test_get_first_phone_number`**: Primary number detection

### 6. Message Processing
- **`test_get_message_type`**: Message type detection (sent/received)
- **`test_get_message_text`**: Text extraction with HTML entity handling
- **`test_get_time_unix`**: Timestamp extraction and conversion

### 7. Error Handling
- **`test_error_handling`**: Custom exception validation
- **`test_edge_cases`**: Boundary condition testing
- **`test_performance_optimizations`**: Caching and optimization validation

### 8. Integration Tests
- **`test_full_conversion_workflow`**: Complete conversion process
- **`test_attachment_processing_integration`**: Attachment handling workflow

## 🔧 Test Dependencies

### Required (Built-in)
- `unittest` - Python's built-in testing framework
- `tempfile` - Temporary file creation
- `shutil` - File operations
- `pathlib` - Path handling
- `datetime` - Date/time operations

### Optional (Enhanced Testing)
- `pytest` - Advanced testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Enhanced mocking capabilities

### Runtime Dependencies
- `beautifulsoup4` - HTML parsing
- `phonenumbers` - Phone number handling
- `python-dateutil` - Date parsing

## 📊 Coverage Analysis

The test suite provides comprehensive coverage of:
- **Function Coverage**: All public functions tested
- **Branch Coverage**: Both success and error paths
- **Exception Coverage**: All custom exceptions tested
- **Edge Case Coverage**: Boundary conditions and error scenarios

## 🧪 Test Data Management

### Temporary File Handling
- Tests create temporary directories for file operations
- Automatic cleanup after each test
- Isolation between test methods

### Mock Objects
- HTML elements mocked for testing
- File system operations mocked where appropriate
- External dependencies isolated

### Test Fixtures
- Common test data in `setUp()` methods
- Reusable test constants
- Consistent test environment

## 🚨 Error Detection

### What Tests Catch
- **Syntax Errors**: Invalid Python code
- **Logic Errors**: Incorrect function behavior
- **Type Errors**: Invalid data type handling
- **Exception Errors**: Missing or incorrect error handling
- **Performance Issues**: Inefficient algorithms

### Common Issues Detected
- Missing exception handling
- Incorrect data type assumptions
- File path handling errors
- XML generation malformation
- Phone number parsing failures

## 🔄 Continuous Integration

### Pre-commit Testing
```bash
# Run tests before committing changes
python3 run_tests.py --quick

# Full test suite for major changes
python3 run_tests.py
```

### Automated Testing
```bash
# GitHub Actions example
- name: Run Tests
  run: |
    python3 -m pip install -r test_requirements.txt
    python3 -m pytest test_sms.py --cov=sms
```

## 📈 Adding New Tests

### Test Method Naming
```python
def test_function_name_scenario(self):
    """Test description of what is being tested."""
    # Test implementation
```

### Test Structure
```python
def test_new_feature(self):
    """Test new feature functionality."""
    # Arrange - Set up test data
    test_input = "test data"
    
    # Act - Execute function under test
    result = sms.new_function(test_input)
    
    # Assert - Verify results
    self.assertEqual(result, "expected output")
```

### Mock Usage
```python
@patch('sms.external_dependency')
def test_with_mock(self, mock_dep):
    mock_dep.return_value = "mocked result"
    # Test implementation
```

## 🎯 Best Practices

### Test Isolation
- Each test is independent
- No shared state between tests
- Clean environment for each test

### Descriptive Names
- Test names clearly describe what is tested
- Use descriptive variable names
- Clear assertion messages

### Comprehensive Coverage
- Test both success and failure paths
- Include edge cases and boundary conditions
- Validate error handling

### Performance Considerations
- Tests should run quickly
- Use mocking for slow operations
- Avoid unnecessary file I/O

## 🚀 Future Enhancements

### Planned Improvements
- **Property-based Testing**: Using hypothesis for data generation
- **Performance Benchmarking**: Timing critical functions
- **Memory Usage Testing**: Memory leak detection
- **Concurrency Testing**: Multi-threaded operation validation

### Test Automation
- **Git Hooks**: Pre-commit test execution
- **CI/CD Integration**: Automated testing in pipelines
- **Test Reporting**: Enhanced result visualization

## 📞 Support

### Running Tests
```bash
# Get help
python3 run_tests.py --help

# Check dependencies
python3 run_tests.py --quick

# Full test suite
python3 run_tests.py
```

### Troubleshooting
- Ensure all dependencies are installed
- Check Python version compatibility (3.7+)
- Verify file permissions for test execution
- Review test output for specific error details

This testing framework ensures that `sms.py` remains robust, maintainable, and reliable as it evolves over time.
