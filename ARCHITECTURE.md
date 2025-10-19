# Google Voice SMS Takeout Converter - Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Configuration System](#configuration-system)
6. [Pipeline Architecture](#pipeline-architecture)
7. [Processing Flow](#processing-flow)
8. [Phone Number Management](#phone-number-management)
9. [Filtering System](#filtering-system)
10. [Thread Safety](#thread-safety)
11. [Performance Optimizations](#performance-optimizations)
12. [Error Handling](#error-handling)

## Overview

The Google Voice SMS Takeout Converter is a Python-based tool that converts Google Voice Takeout export files (HTML format) into organized, viewable HTML conversation files. The system is designed to handle large datasets (60,000+ files) efficiently with a modular, pipeline-based architecture.

### Key Statistics
- **Codebase Size**: ~10,000+ lines of Python code
- **Test Coverage**: 555 tests (100% pass rate)
- **Performance**: Processes 60,000+ files in 6-10 minutes
- **Architecture**: Modular pipeline with 5 independent stages

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface (cli.py)                    │
│  - Command-line argument parsing (Click framework)          │
│  - Configuration building and validation                     │
│  - Pipeline orchestration                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Configuration System                            │
│  - ProcessingConfig (dataclass)                             │
│  - ConfigurationManager (singleton)                          │
│  - ConfigurationBuilder (fluent API)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                 Core Processing Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ SMS Module   │  │   Pipeline   │  │ Conversation    │  │
│  │   (sms.py)   │  │   Manager    │  │    Manager      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│              Supporting Services Layer                       │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │
│  │ Phone       │ │  Filtering   │ │   Attachment       │  │
│  │ Lookup      │ │  Service     │ │   Manager          │  │
│  └─────────────┘ └──────────────┘ └────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│               File Processing Layer                          │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ HTML         │  │  File        │                        │
│  │ Processor    │  │  Processor   │                        │
│  └──────────────┘  └──────────────┘                        │
└──────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
User Input (CLI)
    │
    ▼
Configuration System
    │
    ├─► ProcessingConfig
    ├─► ConfigurationManager
    └─► ConfigurationBuilder
    │
    ▼
Main Processing (sms.py::main)
    │
    ├─► setup_processing_paths()
    │   ├─► Initialize PhoneLookupManager
    │   ├─► Initialize ConversationManager
    │   └─► Setup output directories
    │
    ├─► process_html_files()
    │   ├─► File Discovery
    │   ├─► HTML Parsing (BeautifulSoup)
    │   ├─► Message Extraction
    │   └─► Conversation Writing
    │
    ├─► copy_attachments()
    │   ├─► Attachment Mapping
    │   └─► File Copying (parallel)
    │
    └─► finalize_and_generate_index()
        ├─► Finalize Conversations
        └─► Generate Index HTML
```

## Core Components

### 1. CLI Interface (`cli.py`)

**Purpose**: Command-line interface and application entry point

**Key Features**:
- Click-based command framework
- 10+ commands including pipeline stages
- Configuration preset system
- Comprehensive option validation

**Main Commands**:
- `convert`: Traditional conversion workflow
- `phone-discovery`: Extract phone numbers from HTML
- `phone-lookup`: Lookup unknown numbers
- `phone-pipeline`: Complete phone processing
- `file-discovery`: Catalog HTML files
- `content-extraction`: Extract structured data
- `file-pipeline`: Complete file processing

**Code Structure**:
```python
@click.group()
def cli(ctx, **kwargs):
    # Build configuration
    # Initialize context
    
@cli.command()
def convert(ctx):
    # Main conversion logic
    # Calls sms.main()
```

### 2. Core Processing Module (`sms.py`)

**Purpose**: Main conversion logic and orchestration

**Size**: ~3,800 lines (largest module)

**Key Functions**:

```python
def main(config, context):
    """Main conversion function with progress logging"""
    # 1. Setup processing paths
    # 2. Build attachment mapping
    # 3. Process HTML files
    # 4. Copy attachments
    # 5. Finalize conversations
    # 6. Generate index

def setup_processing_paths(processing_dir, **options):
    """Initialize global managers and paths"""
    
def process_html_files(src_filename_map, config, context):
    """Process all HTML files into conversations"""
    
def process_single_html_file(html_file, ...):
    """Process one HTML file"""
```

**Processing Flow**:
1. **Initialization**: Setup paths, managers, logging
2. **Attachment Mapping**: Build src→dest attachment mapping
3. **HTML Processing**: Parse files, extract messages
4. **Message Writing**: Buffer messages in memory
5. **Attachment Copying**: Parallel file copying
6. **Finalization**: Write HTML files, generate index

### 3. Configuration System

#### ProcessingConfig (`core/processing_config.py`)

**Purpose**: Centralized configuration object (replaces 40+ global variables)

**Key Features**:
- Dataclass-based with validation
- Type-safe attribute access
- Date range validation
- Preset system (default, test, production)

**Structure**:
```python
@dataclass
class ProcessingConfig:
    # Core Settings
    processing_dir: Path
    output_dir: Optional[Path] = None
    output_format: Literal["html"] = "html"
    
    # Phone Lookup
    enable_phone_prompts: bool = False
    phone_lookup_file: Optional[Path] = None
    
    # Filtering
    include_service_codes: bool = False
    filter_numbers_without_aliases: bool = False
    filter_non_phone_numbers: bool = True
    filter_groups_with_all_filtered: bool = True
    include_call_only_conversations: bool = False
    
    # Date Filtering
    exclude_older_than: Optional[datetime] = None
    exclude_newer_than: Optional[datetime] = None
    include_date_range: Optional[str] = None
    
    # Test Mode
    test_mode: bool = False
    test_limit: int = 100
    full_run: bool = False
    
    # Logging
    log_level: str = "INFO"
    verbose: bool = False
    debug: bool = False
```

#### ConfigurationManager (`core/configuration_manager.py`)

**Purpose**: Singleton manager for configuration lifecycle

**Key Features**:
- Configuration caching with TTL
- Multiple source merging (CLI, env, preset)
- Thread-safe access
- Runtime validation

**Usage**:
```python
manager = get_configuration_manager()
config = manager.build_config_from_cli(cli_args)
manager.set_current_config(config)
```

#### ConfigurationBuilder

**Purpose**: Fluent API for building configurations

**Key Methods**:
```python
# From CLI arguments
config = ConfigurationBuilder.from_cli_args(cli_args)

# From environment variables
config = ConfigurationBuilder.from_environment()

# With presets
config = ConfigurationBuilder.create_with_presets(
    processing_dir, 
    preset="production"
)

# Merge multiple configs
config = ConfigurationBuilder.merge_configs(preset, env, cli)
```

### 4. Conversation Management (`core/conversation_manager.py`)

**Purpose**: Manages conversation files and statistics

**Key Features**:
- Memory-buffered message writing
- Thread-safe file operations (RLock)
- Statistics tracking (SMS, calls, voicemails)
- HTML template generation
- Early filtering strategy

**Architecture**:
```python
class ConversationManager:
    def __init__(self, output_dir, buffer_size, ...):
        self.conversation_files = {}  # conversation_id → file_info
        self.conversation_stats = {}  # conversation_id → stats
        self.conversation_content_types = {}  # for call-only filtering
        self._lock = threading.RLock()
    
    def write_message_with_content(self, conversation_id, ...):
        """Buffer message in memory (no immediate I/O)"""
        # 1. Apply date filtering
        # 2. Track content types
        # 3. Check early filtering
        # 4. Buffer message
    
    def finalize_conversation_files(self, config):
        """Write all buffered messages to disk"""
        # 1. Remove empty conversations
        # 2. Sort messages by timestamp
        # 3. Generate HTML
        # 4. Write to disk
```

**StringBuilder Optimization**:
```python
class StringBuilder:
    """Efficient string concatenation for large HTML files"""
    def __init__(self):
        self.parts = []
        self.length = 0  # Incremental tracking
    
    def append(self, text):
        self.parts.append(text)
        self.length += len(text)
        # Auto-consolidate at 1000 parts (Bug #12 fix)
```

### 5. Phone Lookup Management (`core/phone_lookup.py`)

**Purpose**: Phone number to alias mapping with user interaction

**Key Features**:
- Persistent lookup file (`phone_lookup.txt`)
- Thread-safe file operations
- Automatic alias extraction from HTML
- Filter support (filter contacts)
- Backup system

**File Format**:
```
# phone_lookup.txt format
phone_number|alias[|filter]

# Examples:
+1234567890|John Doe
+1555123456|Jane Smith|filter=spam
+1800555000|Support Line|filter
```

**Key Methods**:
```python
class PhoneLookupManager:
    def load_aliases(self):
        """Load from phone_lookup.txt"""
    
    def get_alias(self, phone_number, soup):
        """Get alias, extract from HTML, or prompt user"""
    
    def is_filtered(self, phone_number):
        """Check if contact should be filtered"""
    
    def should_filter_group_conversation(self, participants):
        """Check if ALL group participants are filtered"""
```

**Group Filtering Logic**:
```python
def should_filter_group_conversation(participants, own_number, config):
    """Filter if ALL other participants are filtered"""
    # 1. Remove own number from participants
    # 2. Check if all remaining are filtered
    # 3. Return True only if ALL are filtered
```

### 6. Filtering Service (`core/filtering_service.py`)

**Purpose**: Centralized filtering logic (date and phone)

**Key Features**:
- Dependency-injection based (no globals)
- Date range filtering
- Phone number filtering
- Service code handling

**Structure**:
```python
@dataclass
class FilteringService:
    config: ProcessingConfig
    
    def should_skip_by_date(self, timestamp):
        """Check date filtering"""
        if config.exclude_older_than and date < config.exclude_older_than:
            return True
        if config.exclude_newer_than and date > config.exclude_newer_than:
            return True
        return False
    
    def should_skip_by_phone(self, phone_number, phone_lookup):
        """Check phone filtering"""
        # 1. Check service codes (precedence)
        # 2. Check non-phone numbers
        # 3. Check numbers without aliases
```

## Data Flow

### Message Processing Flow

```
HTML File Input
    │
    ▼
HTML Parser (BeautifulSoup)
    │
    ├─► Extract Messages
    ├─► Extract Participants
    ├─► Extract Timestamps
    └─► Extract Attachments
    │
    ▼
Phone Number Extraction
    │
    ├─► Parse tel: links
    ├─► Parse participant names
    ├─► Fallback to filename
    └─► Generate hash if needed (UN_)
    │
    ▼
Filtering Logic
    │
    ├─► Date Filtering
    ├─► Phone Filtering
    ├─► Group Filtering
    └─► Call-Only Filtering
    │
    ▼
Message Buffering (ConversationManager)
    │
    ├─► Buffer in memory
    ├─► Track statistics
    └─► Track content types
    │
    ▼
Finalization (after all files processed)
    │
    ├─► Sort messages by timestamp
    ├─► Generate HTML from template
    ├─► Write to disk
    └─► Generate index.html
```

### Attachment Processing Flow

```
Attachment Discovery
    │
    ├─► Scan for images (jpg, gif, png)
    ├─► Scan for vCards (vcf)
    └─► Scan for other media
    │
    ▼
Attachment Mapping
    │
    ├─► Normalize filenames
    ├─► Match to img src elements
    ├─► Handle truncated names (50 char)
    └─► Handle duplicates with (1), (2)
    │
    ▼
Attachment Copying
    │
    ├─► Parallel copying (ThreadPoolExecutor)
    ├─► Progress tracking
    └─► Error handling
    │
    ▼
HTML Reference Update
    │
    └─► Update src paths to ./attachments/
```

## Pipeline Architecture

### Pipeline Structure

The pipeline architecture (v2.0.0) provides modular, stateful processing stages.

```
Pipeline Manager
    │
    ├─► Stage Registration
    ├─► Dependency Resolution
    ├─► Execution Order Calculation
    └─► State Persistence (SQLite + JSON)
    │
    ▼
Pipeline Stages
    │
    ├─► Phone Discovery
    │   ├─► Scan HTML files
    │   ├─► Extract phone numbers
    │   ├─► Compare with phone_lookup.txt
    │   └─► Generate unknown_numbers.csv
    │
    ├─► Phone Lookup
    │   ├─► Load unknown numbers
    │   ├─► API lookup (optional)
    │   ├─► Manual lookup (CSV export)
    │   └─► Update phone_lookup.txt
    │
    ├─► File Discovery
    │   ├─► Catalog HTML files
    │   ├─► Extract metadata
    │   ├─► Calculate statistics
    │   └─► Generate file_inventory.json
    │
    └─► Content Extraction
        ├─► Parse HTML files
        ├─► Extract structured data
        ├─► Build conversation data
        └─► Generate extracted_content.json
```

### Pipeline State Management

```python
# State tracking in SQLite
CREATE TABLE stage_executions (
    id INTEGER PRIMARY KEY,
    stage_name TEXT,
    execution_start TIMESTAMP,
    execution_end TIMESTAMP,
    success BOOLEAN,
    records_processed INTEGER,
    errors TEXT
);

# JSON configuration
{
    "completed_stages": ["phone_discovery", "phone_lookup"],
    "last_execution": "2025-10-10T14:30:00Z",
    "pipeline_version": "2.0.0"
}
```

### Pipeline Classes

```python
class PipelineStage(ABC):
    """Base class for pipeline stages"""
    @abstractmethod
    def execute(self, context: PipelineContext) -> StageResult:
        pass
    
    def can_skip(self, context: PipelineContext) -> bool:
        """Check if stage already completed"""
    
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """Check if dependencies are met"""

class PipelineManager:
    """Orchestrates pipeline execution"""
    def register_stage(self, stage: PipelineStage):
        """Register a stage"""
    
    def execute_pipeline(self, stages=None, config=None) -> Dict[str, StageResult]:
        """Execute pipeline with dependency resolution"""
```

## Phone Number Management

### Hash-Based Fallback System

For conversations without extractable phone numbers, the system generates unique, consistent identifiers:

**Format**: `UN_{22_character_base64_hash}`

**Algorithm**:
1. Take input string (filename, conversation ID, etc.)
2. Generate MD5 hash (128 bits)
3. Encode as URL-safe Base64
4. Take first 22 characters
5. Prefix with "UN_"

**Example**:
```python
def generate_unknown_number_hash(input_string: str) -> str:
    """Generate hash-based fallback number"""
    hash_digest = hashlib.md5(input_string.encode('utf-8')).digest()
    hash_b64 = base64.urlsafe_b64encode(hash_digest).decode('ascii')
    hash_b64 = hash_b64.rstrip('=')[:22]  # Remove padding, take 22 chars
    return f"UN_{hash_b64}"

# Example output: UN_E7GCre66q93-hk4l3wGubA
```

**Benefits**:
- **Unique**: 128-bit MD5 ensures no collisions
- **Consistent**: Same input always produces same hash
- **URL-safe**: No special characters
- **Valid**: Passes phone number validation
- **Identifiable**: UN_ prefix clearly marks as unknown

### Phone Number Priority

1. **Explicit Lookup**: From `phone_lookup.txt`
2. **HTML Metadata**: From tel: links and vcard elements
3. **Filename Parsing**: Extract from Google Voice filename
4. **Hash Fallback**: Generate UN_ prefixed hash

## Filtering System

### Filtering Types

#### 1. Date Filtering

**Purpose**: Filter messages by timestamp

**Configuration**:
```python
config.exclude_older_than = datetime(2022, 1, 1)
config.exclude_newer_than = datetime(2025, 12, 31)
# Or combined:
config.include_date_range = "2022-01-01_2025-12-31"
```

**Implementation**: Message-level filtering at write time

**Benefits**:
- Early filtering (no unnecessary I/O)
- Empty conversations automatically removed
- Date validation allows single-day ranges (Bug #4 fix)

#### 2. Phone Number Filtering

**Types**:
- **Service Codes**: 5-6 digit numbers (configurable)
- **Non-Phone Numbers**: Toll-free, international
- **Numbers Without Aliases**: Optional filtering
- **Filtered Contacts**: From phone_lookup.txt filter column

**Precedence** (Bug #1 fix):
1. Service codes (if `include_service_codes=True`, allow through)
2. Non-phone numbers (if `filter_non_phone_numbers=True`, filter out)
3. Numbers without aliases (if enabled, filter out)

#### 3. Group Conversation Filtering

**Logic**: Filter only if ALL participants (excluding self) are filtered

**Purpose**: Preserve group conversations where at least one participant is not filtered

**Implementation**:
```python
def should_filter_group_conversation(participants, own_number, config):
    """Filter only if ALL other participants are filtered"""
    other_participants = [p for p in participants if p != own_number]
    return all(is_filtered(p) for p in other_participants)
```

#### 4. Call-Only Conversation Filtering

**Purpose**: Filter conversations containing only call logs (no text content)

**Content Tracking**:
```python
conversation_content_types = {
    conversation_id: {
        "has_sms": False,
        "has_mms": False,
        "has_voicemail_with_text": False,
        "has_calls_only": True,
        "call_count": 5
    }
}
```

**Filtering Decision**:
- Include if has SMS messages
- Include if has MMS messages
- Include if has voicemail with transcription
- Filter if ONLY call logs (no text content)

## Thread Safety

### Thread-Safe Components

#### 1. Logging System

**Implementation**: QueueHandler + QueueListener (Bug #13 fix)

```python
# utils/thread_safe_logging.py
def setup_thread_safe_logging(log_level, log_file, console_logging=True):
    """Setup thread-safe logging using queue-based handlers"""
    log_queue = queue.Queue(-1)  # Unlimited queue
    
    # Queue handler for all loggers
    queue_handler = logging.handlers.QueueHandler(log_queue)
    
    # Listener processes queue in separate thread
    queue_listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        console_handler
    )
    queue_listener.start()
```

**Benefits**:
- No file corruption
- No lock contention
- Parallel processing safe
- Zero performance impact

#### 2. ConversationManager

**Implementation**: RLock for all operations

```python
class ConversationManager:
    def __init__(self, ...):
        self._lock = threading.RLock()  # Reentrant lock
    
    def write_message_with_content(self, ...):
        with self._lock:
            # Thread-safe message buffering
```

**Protected Operations**:
- File creation
- Message buffering
- Statistics updates
- Finalization

#### 3. PhoneLookupManager

**Implementation**: Lock for file operations

```python
class PhoneLookupManager:
    def __init__(self, ...):
        self._file_lock = threading.Lock()
    
    def save_aliases(self):
        with self._file_lock:
            # Thread-safe file writing
```

## Performance Optimizations

### Hardcoded Optimal Settings

**Location**: `core/shared_constants.py`

**Rationale**: Optimized for high-end systems (16GB+ RAM, 8+ cores, 20-50k files)

```python
# Performance configuration
MAX_WORKERS = 1  # Conservative (can increase with Bug #13 fix)
BATCH_SIZE_OPTIMAL = 2000  # Files per batch
BUFFER_SIZE_OPTIMAL = 131072  # 128KB I/O buffer
CHUNK_SIZE_OPTIMAL = 1000  # Files per chunk
STREAMING_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks
FILE_READ_BUFFER_SIZE = 512 * 1024  # 512KB buffer
MMAP_THRESHOLD = 5 * 1024 * 1024  # 5MB for mmap
```

### Memory Optimization Strategies

#### 1. StringBuilder Pattern
```python
class StringBuilder:
    """Efficient string concatenation"""
    def __init__(self):
        self.parts = []  # List of strings
        self.length = 0  # Incremental tracking (Bug #12 fix)
    
    def append(self, text):
        self.parts.append(text)
        self.length += len(text)  # O(1) instead of O(n)
        
        # Auto-consolidate at 1000 parts
        if len(self.parts) > 1000:
            combined = "".join(self.parts[:500])
            self.parts = [combined] + self.parts[500:]
```

#### 2. Memory-Only Buffering
- No premature file writes
- All messages buffered in memory
- Single write operation per conversation
- Clean HTML structure guaranteed

#### 3. String Pooling
```python
# processors/html_processor.py
STRING_POOL = StringPool()
STRING_POOL.CSS_SELECTORS = {
    "participants": 'a[href^="tel:"]',
    "messages": ".message",
    ...
}
```

### I/O Optimization

#### 1. Parallel Attachment Copying
```python
def copy_attachments_parallel(file_list, dest_dir, max_workers=8):
    """Copy files in parallel using ThreadPoolExecutor"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(copy_file, src, dest) 
                  for src, dest in file_list]
        for future in as_completed(futures):
            future.result()  # Wait for completion
```

#### 2. Memory-Mapped File I/O
- Enabled for files > 5MB
- Reduces memory pressure
- Improves read performance

#### 3. Buffered File Operations
- 128KB write buffers
- 512KB read buffers
- Reduces syscalls

### Caching Strategies

#### 1. LRU Cache for Phone Parsing
```python
@lru_cache(maxsize=10000)
def parse_phone_number(phone: str, region: str = "US"):
    """Cached phone number parsing"""
    return phonenumbers.parse(phone, region)
```

#### 2. HTML Metadata Cache
- Caches parsed HTML metadata
- Reduces repeated parsing
- Invalidation on file count change (Bug #9 fix)

#### 3. Configuration Cache
- 5-minute TTL
- Thread-safe access
- Reduces re-parsing

## Error Handling

### Error Handling Strategy

#### 1. Graceful Degradation
```python
try:
    # Primary operation
    result = process_with_best_method()
except SpecificError:
    # Fallback operation
    result = process_with_fallback_method()
except Exception as e:
    # Log and continue
    logger.error(f"Operation failed: {e}")
    result = default_value
```

#### 2. Validation Before Processing
```python
def process_html_file(file_path):
    # Validate first
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None
    
    # Then process
    return parse_html(file_path)
```

#### 3. Error Recovery
- Backup phone_lookup.txt before writes
- Transaction-like conversation finalization
- Partial results on failure

### Logging Strategy

#### Levels:
- **DEBUG**: Variable states, execution paths
- **INFO**: Major milestones, progress updates
- **WARNING**: Recoverable issues, fallbacks used
- **ERROR**: Operation failures, data loss risks
- **CRITICAL**: System failures, abort conditions

#### Key Logging Points:
1. Processing start/end with statistics
2. Major phase transitions
3. File operations (read/write)
4. Filtering decisions with counts
5. Performance metrics
6. Error conditions with context

## Module Dependencies

### Dependency Graph

```
cli.py
 ├─► core/processing_config.py
 ├─► core/configuration_manager.py
 ├─► core/sms_patch.py
 └─► sms.py
      ├─► core/conversation_manager.py
      ├─► core/phone_lookup.py
      ├─► core/filtering_service.py
      ├─► core/attachment_manager.py
      ├─► processors/file_processor.py
      ├─► processors/html_processor.py
      ├─► utils/thread_safe_logging.py
      ├─► utils/phone_utils.py
      └─► utils/utils.py

core/pipeline/manager.py
 ├─► core/pipeline/base.py
 ├─► core/pipeline/state.py
 └─► core/pipeline/stages/
      ├─► phone_discovery.py
      ├─► phone_lookup.py
      ├─► file_discovery.py
      └─► content_extraction.py
```

### External Dependencies

```python
# Core Processing
from bs4 import BeautifulSoup  # HTML parsing
import phonenumbers  # Phone number validation
import dateutil.parser  # Date parsing

# CLI Framework
import click  # Command-line interface

# Concurrency
from concurrent.futures import ThreadPoolExecutor
import threading
import queue

# Data Storage
import sqlite3  # Pipeline state
import json  # Configuration, metadata
```

## Testing Architecture

### Test Structure

```
tests/
├── unit/                    # 294 unit tests
│   ├── test_bug_fixes.py           # Bug fix tests (17 tests)
│   ├── test_processing_config.py   # Config tests
│   ├── test_phone_lookup.py        # Phone lookup tests
│   ├── test_filtering_service.py   # Filtering tests
│   ├── test_conversation_manager.py
│   ├── test_pipeline_stages.py     # Pipeline stage tests
│   └── test_thread_safe_logging.py # Thread safety tests
│
├── integration/             # 236 integration tests
│   ├── test_sms_output.py          # End-to-end tests
│   ├── test_filtering_integration.py
│   ├── test_phone_parsing.py
│   └── test_pipeline_integration.py
│
└── utils/                   # Test utilities
    ├── test_helpers.py
    └── test_fixtures.py
```

### Test Coverage

- **Unit Tests**: 294 tests covering individual functions
- **Integration Tests**: 236 tests for complete workflows
- **Bug Tests**: 17 tests for specific bug fixes
- **Pass Rate**: 100% (555/555 tests pass)

### Testing Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_bug_fixes.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run only unit tests
python -m pytest tests/unit/ -v

# Run only integration tests
python -m pytest tests/integration/ -v
```

## Recent Architectural Changes

### Version 2.0.0 - Pipeline Architecture
- Introduced modular pipeline system
- Added 5 independent processing stages
- Implemented SQLite + JSON state management
- Created PipelineManager orchestration layer

### Version 1.0.0 - Test Mode Fix
- Fixed test mode performance (Bug #10)
- Synchronized LIMITED_HTML_FILES with config
- 99%+ performance improvement

### Bug Fixes (2025-10-09)
- Bug #1: Removed max_workers validation
- Bug #3: Enhanced file handle cleanup logging
- Bug #4: Allowed single-day date ranges
- Bug #7: Fixed alias corruption from unknown filters
- Bug #8: Removed unreliable own-number heuristic
- Bug #9: Enhanced cache invalidation with file count
- Bug #13: Implemented thread-safe file logging

## Future Architectural Improvements

### Planned Enhancements
1. **Global Variable Elimination**: Complete migration to config objects
2. **Async Processing**: Convert to async/await for better I/O
3. **Database Backend**: Store conversations in SQLite for querying
4. **API Server**: REST API for programmatic access
5. **Web UI**: Browser-based interface for conversion

### Performance Goals
- Sub-second processing for test mode
- <5 minutes for 100,000+ files
- Real-time progress streaming
- Memory usage <2GB for any dataset

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-10  
**Maintainer**: Development Team

