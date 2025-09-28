# Release Notes

## Version 2.0.0 - Pipeline Architecture Implementation (September 28, 2025)

### 🚀 **MAJOR RELEASE - Complete Modernization**

This is a major architectural overhaul that transforms the Google Voice SMS converter into a modern, modular pipeline system while maintaining 100% backward compatibility.

#### **🏗️ New Pipeline Architecture**
- **Modular Design**: 5 independent, rerunnable pipeline stages
- **State Management**: SQLite + JSON hybrid for persistent stage tracking
- **CLI Integration**: Individual stage commands + combined pipeline workflows
- **Performance**: Optimized processing with parallel operations and caching
- **Reliability**: Comprehensive error handling and recovery mechanisms

#### **📱 Phone Number Management**
- **Phone Discovery**: Automated extraction of 9,000+ phone numbers from HTML files
- **Phone Lookup**: API integration (Truecaller, Twilio) + manual lookup workflows
- **Smart Caching**: Persistent phone directory with automatic alias management
- **CLI Commands**: `phone-discovery`, `phone-lookup`, `phone-pipeline`

#### **📁 File Processing Enhancement**
- **File Discovery**: Intelligent cataloging of 62,000+ HTML files with metadata
- **Content Extraction**: Structured data parsing with conversation analysis
- **Batch Processing**: Efficient handling of large datasets with progress tracking
- **CLI Commands**: `file-discovery`, `content-extraction`, `file-pipeline`

#### **🧪 Testing & Quality**
- **Comprehensive Test Suite**: 529 total tests (513 passed, 16 skipped, 0 failed)
- **New Pipeline Tests**: 25 dedicated unit tests for pipeline stages
- **Zero Regressions**: All existing functionality preserved and verified
- **Clean Codebase**: Removed 3,840+ lines of deprecated code across 69+ files

#### **📚 Documentation**
- **Pipeline Usage Guide**: Complete documentation for new architecture
- **Updated README**: Comprehensive usage instructions and examples
- **CLI Help**: Detailed help for all commands and options

#### **🔄 Backward Compatibility**
- **Legacy Commands**: All existing CLI commands work unchanged
- **Configuration**: Existing config files and options fully supported
- **Output Format**: Identical HTML output structure maintained

### **New CLI Commands**
```bash
# Pipeline workflows (new in v2.0.0)
python cli.py phone-pipeline      # Discover and lookup phone numbers
python cli.py file-pipeline       # Process files and extract content

# Individual stages
python cli.py phone-discovery     # Extract phone numbers from HTML files
python cli.py phone-lookup        # Lookup unknown numbers (API/manual)
python cli.py file-discovery      # Catalog and analyze HTML files
python cli.py content-extraction  # Extract structured conversation data

# Legacy commands (still fully supported)
python cli.py convert             # Full conversion (original command)
```

### **🐛 Bug Fixes**
- **Service Code Filtering**: Fixed precedence bug in filtering logic
- **BeautifulSoup Warnings**: Updated deprecated `text=` to `string=` parameter  
- **Date Filtering**: Fixed config passing issue in file processor
- **Test Suite**: All 529 tests pass with zero warnings

---

## Version 1.0.0 - Test Mode Performance Fix (September 20, 2025)

### 🚀 Major Improvements

#### Critical Bug Fix: Test Mode Performance Issue
- **Issue**: `--test-mode --test-limit N` was processing ALL files instead of just N files, causing extremely long execution times (hours)
- **Fix**: Synchronized global `LIMITED_HTML_FILES` variable with context configuration
- **Impact**: Test mode now processes exactly the specified number of files
- **Performance**: Execution time reduced from hours to seconds (99%+ improvement)

### 🧪 Test Mode Improvements
- **Before**: `--test-mode --test-limit 5` processed all files (potentially thousands)
- **After**: `--test-mode --test-limit 5` processes exactly 5 files
- **User Experience**: Test mode now works as expected for quick testing and validation

### 🔧 Technical Changes
- **Files Modified**: 
  - `sms.py`: Added global variable synchronization (2 lines)
  - `tests/test_test_mode_bug.py`: Added comprehensive test suite
- **Risk Level**: Low (minimal code changes, easy rollback)
- **Backward Compatibility**: Maintained (no breaking changes)

### 📊 Performance Metrics
| Metric | Before Fix | After Fix | Improvement |
|--------|------------|-----------|-------------|
| Files Processed | All files | Limited count | ✅ Correct |
| Execution Time | Hours | < 1 second | 99%+ faster |
| Test Mode Working | ❌ No | ✅ Yes | Fixed |
| User Experience | Poor | Excellent | Dramatically improved |

### 🧪 Testing Completed
- ✅ Unit tests: 6 tests (3 bug reproduction + 3 fix validation)
- ✅ Integration tests: CLI functionality validation
- ✅ Performance tests: Real-world scenario testing
- ✅ Regression tests: Full-run mode validation
- ✅ All tests passing

### 📝 Documentation Updates
- ✅ README.md updated with fix information
- ✅ CLI help text updated with fix notes
- ✅ Deployment documentation created
- ✅ Release notes created

### 🎯 User Impact
- **Immediate**: Test mode now works correctly
- **Performance**: Dramatic speed improvement for testing
- **Reliability**: Comprehensive test coverage prevents future regressions
- **Usability**: Users can now effectively test conversions with small datasets

### 🔄 Migration Notes
- **No migration required**: Fix is automatic
- **No configuration changes**: Existing settings work as expected
- **No data loss**: All functionality preserved

### 🛡️ Rollback Plan
If issues are detected, rollback is simple:
```bash
git revert <commit-hash>
git push origin main
```

### 📞 Support
For issues or questions regarding this release:
- Check the deployment notes: `DEPLOYMENT_NOTES.md`
- Review test results: `tests/test_test_mode_bug.py`
- Contact: [Technical Lead]

---

## Previous Versions

### Version 0.x.x - Legacy Versions
- Initial implementation with test mode performance issue
- Various improvements from community forks
- Performance optimizations and bug fixes

---

## Future Roadmap

### Planned Improvements
- **Phase 2**: Architectural cleanup (eliminate global variables)
- **Phase 3**: Enhanced test coverage and performance monitoring
- **Phase 4**: Configuration system modernization

### Known Issues
- None (test mode performance issue resolved)

### Deprecation Notices
- None

---

*Release notes generated on September 20, 2025*