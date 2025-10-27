# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Google Voice SMS Takeout HTML Converter - Converts Google Voice Takeout export files into organized, searchable HTML conversations. The project processes 60,000+ HTML files, manages complex phone number lookups, and generates clean conversation archives with full threading support.

## ⚠️ IMPORTANT: Virtual Environment

**ALWAYS activate the virtual environment before running any Python commands.**

```bash
# Activate venv FIRST (every time you run Python commands)
source env/bin/activate  # macOS/Linux
env\Scripts\activate.bat  # Windows

# Then run your Python commands
python -m pytest tests/ -v
python cli.py --help
```

**Why**: This project uses dependencies (click, pytest, beautifulsoup4, etc.) that are only available in the virtual environment. Running Python commands without activating venv will result in `ModuleNotFoundError`.

**Common mistake**: Running `python3 cli.py` directly without `source env/bin/activate` first.

## Common Commands

### Testing
```bash
# Run all tests (550 tests)
python -m pytest tests/ -v --tb=short

# Run specific test file
python -m pytest tests/unit/test_bug_fixes.py -v

# Run specific test class
python -m pytest tests/unit/test_bug_fixes.py::TestBug4DateRangeValidation -v

# Run with minimal output
python -m pytest tests/ -v --tb=no

# Run only unit tests
python -m pytest tests/unit/ -v

# Run only integration tests
python -m pytest tests/integration/ -v
```

### Development Setup
```bash
# Create virtual environment
python -m venv env

# Activate virtual environment
source env/bin/activate  # macOS/Linux
env\Scripts\activate.bat  # Windows

# Install dependencies
python -m pip install -r config/requirements.txt
```

### Running the Converter
```bash
# Test mode (processes 100 files only)
python cli.py --test-mode convert

# Full conversion
python cli.py --full-run convert

# With date filtering
python cli.py --include-date-range 2022-01-01_2024-12-31 convert

# With configuration validation
python cli.py validate
```

### Pipeline Commands (New v2.0 Architecture)
```bash
# Phone number discovery and lookup
python cli.py phone-pipeline

# File discovery and content extraction
python cli.py file-pipeline --max-files 80000

# Phases 1-4: Complete pipeline for HTML generation with attachments
python cli.py attachment-mapping         # Phase 1: Build attachment mapping
python cli.py attachment-copying         # Phase 2: Copy attachments
python cli.py html-generation            # Phase 3a: Generate HTML conversations
python cli.py index-generation           # Phase 4: Generate index.html

# HTML generation with filtering (Bug #17 fixed - filters now work!)
python cli.py --filter-non-phone-numbers --no-include-call-only-conversations html-generation
python cli.py --include-date-range 2020-01-01_2024-12-31 html-generation

# Individual discovery stages
python cli.py phone-discovery
python cli.py phone-lookup --provider manual
python cli.py file-discovery
python cli.py content-extraction --max-files 80000

# Cache management
python cli.py clear-cache --all          # Clear both caches
python cli.py clear-cache --attachment   # Clear attachment cache only
python cli.py clear-cache --pipeline     # Clear pipeline state only
```

**Important**: CLI filtering options (like `--filter-non-phone-numbers`) must come BEFORE the command name.

**See also**: `docs/CACHE_MANAGEMENT.md` for detailed cache behavior explanation

## Architecture Overview

### Core Design Pattern: Configuration Object Pattern

The codebase uses a **Configuration Object Pattern** to eliminate global variables and provide centralized, validated configuration:

- **`ProcessingConfig`** (`core/processing_config.py`): Central configuration dataclass that replaces ~40 global variables
- **`ConfigurationManager`** (`core/configuration_manager.py`): Singleton manager for configuration lifecycle
- **`ConfigurationBuilder`**: Fluent API for building configs from CLI args, environment, or presets

### Module Patching System

The project uses a sophisticated **module patching** system to inject configuration into the legacy `sms.py` module without breaking changes:

- **`core/sms_patch.py`**: Patches global variables and function signatures in `sms.py`
- Enables gradual migration from globals to config objects
- All patches are reversible and trackable
- **Important**: Always unpatch after conversion to avoid state leakage

### Pipeline Architecture (v2.0)

Modular, stateful pipeline for processing large datasets:

```
core/pipeline/
├── base.py           # Base classes: PipelineStage, PipelineResult
├── manager.py        # PipelineManager orchestrates stage execution
├── state.py          # PipelineState tracks completion, caching, resumability
└── stages/
    ├── phone_discovery.py    # Discovers 9,000+ phone numbers
    ├── phone_lookup.py       # API integration for number enrichment
    ├── file_discovery.py     # Catalogs 60,000+ HTML files
    └── content_extraction.py # Extracts structured message data
```

**Key Concepts**:
- **Stages are idempotent**: Can be re-run safely, automatically skip if completed
- **State persistence**: JSON files in `conversations/` track pipeline progress
- **Resumable**: Interrupted pipelines continue from last successful stage
- **Independent execution**: Stages can run individually or as full pipeline

### Core Processing Flow

1. **Setup** (`sms.py:setup_processing_paths`)
   - Initializes `PhoneLookupManager` (loads `phone_lookup.txt`)
   - Sets up output directories
   - Validates processing paths

2. **HTML Processing** (`processors/html_processor.py`)
   - Parses Google Voice export HTML with BeautifulSoup
   - Extracts messages, participants, timestamps
   - Handles SMS, MMS, group conversations, calls, voicemails

3. **Conversation Management** (`core/conversation_manager.py`)
   - Manages in-memory buffering of messages (no premature file writes)
   - Generates conversation IDs from participants
   - Tracks statistics (SMS count, call count, attachments)
   - **Critical**: All messages buffered until `finalize_conversation_files()`

4. **Filtering System** (`core/filtering_service.py`)
   - Date range filtering: `exclude_older_than`, `exclude_newer_than`, `include_date_range`
   - Phone number filtering: toll-free, service codes, groups
   - Call-only conversation filtering (new feature)
   - **Early filtering strategy**: Decisions made at message write time

5. **Template-Based HTML Generation** (`templates/`)
   - Conversation HTML: `templates/conversation.html`
   - Index HTML: `templates/index.html`
   - Uses Python `.format()` for variable substitution

### Phone Number Handling

**Hash-Based Fallback System**:
- Format: `UN_{22_char_base64}` (total 25 chars)
- Algorithm: MD5 hash → Base64 URL-safe encoding
- Used when phone numbers cannot be extracted
- Ensures consistent, unique identifiers

**Phone Lookup Priority**:
1. `phone_lookup.txt` (user-provided aliases)
2. Google Voice HTML metadata
3. Filename parsing (regex extraction)
4. Hash-based fallback (guaranteed unique)

### Test Mode Performance Fix (v1.0.0)

**Critical Fix**: Test mode now correctly limits processing to `--test-limit` files.

Previously, `--test-mode --test-limit 100` would process ALL files (60,000+) causing hour-long executions. The fix synchronized the global `LIMITED_HTML_FILES` variable with context configuration, reducing test mode execution from hours to seconds.

**Usage**:
```bash
# Correct test mode usage (processes exactly 100 files)
python cli.py --test-mode --test-limit 100 convert
```

## Critical Implementation Details

### Memory Management

**StringBuilder** (`core/conversation_manager.py:23-44`):
- Efficient string concatenation for large HTML files
- Auto-consolidates when parts list exceeds 1000 items
- **Bug Fix #12**: Length tracking optimized to avoid recalculation

**Buffering Strategy**:
- Messages buffered in memory until finalization
- No premature file writes (ensures clean HTML structure)
- Buffer size: 32KB (optimal for most systems)

### Filtering Architecture

**Early Filtering** (Performance Optimization):
- Filter decisions made during message write, not at finalization
- Prevents unnecessary file I/O for filtered conversations
- Implemented in `ConversationManager._should_create_conversation_file()`

**Call-Only Filtering**:
- Tracks content types per conversation (SMS/MMS/voicemail/call)
- Filters conversations containing ONLY call logs (no text content)
- Configurable via `--include-call-only-conversations`

### Date Range Validation

**Bug Fix #4**: Single-day date ranges are now valid.

```python
# Valid single-day filtering (fixed in v1.0.0)
--include-date-range 2024-01-01_2024-01-01

# Validation now uses > instead of >=
if start_date > end_date:  # Allows start_date == end_date
    raise ValueError(...)
```

### Thread Safety

- **PhoneLookupManager**: Thread-safe with RLock for concurrent reads/writes
- **ConversationManager**: Thread-safe buffering with RLock
- **String Pool**: Shared string deduplication (thread-safe)
- **File Logging**: DISABLED to prevent corruption (console-only logging)

## File Structure Highlights

```
gvoice-sms-takeout-xml/
├── cli.py                    # Click-based CLI with 10+ commands
├── sms.py                    # Core conversion logic (legacy, being refactored)
├── core/
│   ├── processing_config.py      # Configuration dataclass
│   ├── configuration_manager.py  # Singleton config manager
│   ├── sms_patch.py             # Module patching system
│   ├── conversation_manager.py  # Message buffering & HTML generation
│   ├── phone_lookup.py          # Phone number alias management
│   ├── filtering_service.py     # Filtering logic & validation
│   └── shared_constants.py      # Hardcoded performance constants
├── processors/
│   ├── html_processor.py        # Google Voice HTML parsing
│   └── file_processor.py        # File processing orchestration
├── templates/
│   ├── conversation.html        # Per-conversation HTML template
│   └── index.html              # Main index with statistics
└── tests/
    ├── unit/                    # 250+ unit tests
    └── integration/             # 300+ integration tests
```

## Important Patterns & Conventions

### Configuration Usage

```python
# Always use ProcessingConfig, never global variables
from core.processing_config import ProcessingConfig

def my_function(config: ProcessingConfig):
    # Access configuration
    processing_dir = config.processing_dir
    test_limit = config.get_test_limit()  # -1 if not in test mode
```

### Module Patching Workflow

```python
from core.sms_patch import patch_sms_module, unpatch_sms_module

# Patch before using sms.py functions
patcher = patch_sms_module(config)

# Use sms.py functions
from sms import process_html_files
process_html_files(...)

# ALWAYS unpatch after use
unpatch_sms_module(patcher)
```

### Conversation Manager Pattern

```python
from core.conversation_manager import ConversationManager

# Initialize
manager = ConversationManager(
    output_dir=Path("conversations"),
    buffer_size=32768,
    output_format="html"
)

# Write messages (buffered in memory)
manager.write_message_with_content(
    conversation_id="Alice",
    timestamp=1234567890000,
    sender="Alice",
    message="Hello!",
    message_type="sms",
    config=processing_config
)

# Finalize (writes all buffered messages to disk)
manager.finalize_conversation_files(config)

# Generate index
manager.generate_index_html(stats, elapsed_time)
```

## Known Issues & Workarounds

### File Logging Disabled
**Issue**: File logging causes corruption in multi-threaded environments
**Workaround**: Console-only logging (see `cli.py:36-63`)
**Future Fix**: Implement QueueHandler for thread-safe file logging

### Test Mode Limit
**Issue**: Previously processed all files regardless of `--test-limit`
**Status**: FIXED in v1.0.0 (synchronized globals with config)

### Hash Collisions
**Issue**: Old 6-8 digit hashes could collide
**Status**: FIXED - New system uses full 128-bit MD5 (22-char Base64)

## Performance Characteristics

- **Small datasets** (< 1,000 messages): Sub-second processing
- **Medium datasets** (10,000 - 50,000 messages): 30-60 seconds
- **Large datasets** (100,000+ messages): 6-10 minutes
- **Test mode**: 2-5 seconds (processes exactly `--test-limit` files)

**Optimized for**:
- 16GB+ RAM
- 8+ CPU cores
- NVMe SSD storage
- 20,000-60,000 HTML files

## Code Quality Standards

### Bug Fixes
When fixing bugs, follow the established pattern in `tests/unit/test_bug_fixes.py`:
1. Create failing test that reproduces bug
2. Implement fix
3. Verify test passes
4. Document in `BUG_FIXES_SUMMARY.md`

### Performance Optimizations
- Avoid unnecessary `sum()` or length recalculations (see Bug #12)
- Remove redundant error handling (see Bug #6)
- Use early filtering to prevent I/O waste
- Prefer in-memory buffering over streaming writes

### Testing Requirements
- All new features require unit tests
- Integration tests for end-to-end workflows
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Maintain 100% test pass rate (550/550 tests)
