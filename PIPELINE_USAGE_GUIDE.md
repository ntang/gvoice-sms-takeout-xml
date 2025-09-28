# Pipeline Architecture Usage Guide

## 🚀 Overview

The Google Voice SMS Converter now includes a powerful **modular pipeline architecture** that allows you to run processing stages independently or together. This provides better control, debugging capabilities, and the ability to resume interrupted processing.

## 📋 Quick Reference

### Original Workflow (Still Available)
```bash
# Traditional conversion (works exactly as before)
python cli.py --full-run convert
python cli.py --test-mode --test-limit 100 convert
```

### New Pipeline Capabilities
```bash
# Individual stages
python cli.py phone-discovery        # Discover phone numbers
python cli.py phone-lookup --provider manual  # Phone lookup
python cli.py file-discovery         # Catalog HTML files
python cli.py content-extraction     # Extract structured data

# Complete pipelines
python cli.py phone-pipeline         # Complete phone processing
python cli.py file-pipeline          # Complete file processing
```

## 🔧 Pipeline Stages

### 1. Phone Discovery Stage
**Purpose**: Discovers and catalogs all phone numbers from HTML files

**Command**: `python cli.py phone-discovery`

**What it does**:
- Scans all HTML files in your Google Voice export
- Extracts phone numbers using multiple regex patterns
- Normalizes phone numbers to consistent format (+1xxxxxxxxxx)
- Compares against existing phone_lookup.txt to identify unknown numbers
- Creates comprehensive phone inventory

**Output Files**:
- `conversations/phone_inventory.json` - Complete phone number catalog
- Console output with discovery statistics

**Example Output**:
```
🔍 Starting phone number discovery...
✅ Discovery completed successfully!
   📊 Discovered: 9,046 phone numbers
   ❓ Unknown: 8,639 numbers
   ✓ Known: 407 numbers
   📁 Files processed: 61,484
```

### 2. Phone Lookup Stage
**Purpose**: Performs lookup and enrichment of unknown phone numbers

**Commands**:
```bash
# Manual mode (exports CSV for manual research)
python cli.py phone-lookup --provider manual

# API mode (requires API key)
python cli.py phone-lookup --provider ipqualityscore --api-key YOUR_KEY
```

**Dependencies**: Requires phone-discovery to be completed first

**What it does**:
- Loads unknown numbers from phone discovery
- Performs lookup using configured provider
- Manual mode: Exports CSV for manual research
- API mode: Queries spam/fraud detection services
- Updates phone_lookup.txt with new entries
- Stores results in SQLite database

**Output Files**:
- `conversations/phone_directory.sqlite` - Lookup results database
- `conversations/unknown_numbers.csv` - Manual lookup export (manual mode)
- Updated `phone_lookup.txt` - Traditional phone lookup file

### 3. File Discovery Stage
**Purpose**: Catalogs all HTML files and identifies their types

**Command**: `python cli.py file-discovery`

**What it does**:
- Scans processing directory for HTML files
- Identifies file types (SMS/MMS, Calls, Voicemails)
- Extracts metadata (size, dates, content indicators)
- Creates comprehensive file inventory

**Output Files**:
- `conversations/file_inventory.json` - Complete file catalog

**Example Output**:
```
📁 Starting file discovery...
✅ File discovery completed successfully!
   📊 Total files: 62,314
   📁 File types: {'calls': 61,484, 'sms_mms': 830}
   💾 Total size: 194.02 MB
   🔍 Largest file: 3.76 MB
```

### 4. Content Extraction Stage
**Purpose**: Extracts structured data from HTML files

**Commands**:
```bash
# Default batch size (1000 files)
python cli.py content-extraction

# Custom batch size
python cli.py content-extraction --max-files 500
```

**Dependencies**: Requires file-discovery to be completed first

**What it does**:
- Processes HTML files in configurable batches
- Extracts messages, timestamps, participants
- Identifies attachments and media references
- Creates normalized conversation data structures

**Output Files**:
- `conversations/extracted_content.json` - Structured conversation data

## 🔄 Complete Pipeline Commands

### Phone Processing Pipeline
**Command**: `python cli.py phone-pipeline`

**What it does**:
1. Runs phone-discovery (if not already completed)
2. Runs phone-lookup in manual mode (if not already completed)
3. Provides complete phone number analysis

**Options**:
```bash
# With API integration
python cli.py phone-pipeline --api ipqualityscore --api-key YOUR_KEY
```

### File Processing Pipeline
**Command**: `python cli.py file-pipeline`

**What it does**:
1. Runs file-discovery (if not already completed)
2. Runs content-extraction with default settings (if not already completed)
3. Provides complete file analysis

**Options**:
```bash
# Custom batch size
python cli.py file-pipeline --max-files 500
```

## 💾 Data Storage Locations

### Pipeline State
```
conversations/pipeline_state/
├── pipeline_state.db          # SQLite execution tracking
└── pipeline_config.json       # JSON configuration state
```

### Stage Outputs
```
conversations/
├── phone_inventory.json       # Phone discovery results
├── phone_directory.sqlite     # Phone lookup database
├── unknown_numbers.csv        # Manual lookup export
├── file_inventory.json        # File discovery results
├── extracted_content.json     # Content extraction results
└── [existing conversation files...]  # Original output preserved
```

### Traditional Files (Still Used)
```
phone_lookup.txt               # Traditional phone lookup file (updated by pipeline)
conversations/index.html       # Main conversation index
conversations/*.html           # Individual conversation files
conversations/attachments/     # Copied attachments
```

## 🔄 State Management

### Automatic Stage Skipping
The pipeline automatically tracks completed stages and skips them on subsequent runs:

```bash
# First run - executes discovery
python cli.py phone-discovery
# Output: ✅ Discovery completed successfully!

# Second run - skips discovery
python cli.py phone-discovery  
# Output: ⏭️ Stage was skipped (already completed)
```

### Clearing Stage State
To force re-execution of stages, clear the pipeline state:

```bash
# Clear all pipeline state
rm -rf conversations/pipeline_state

# Clear specific stage state (advanced)
# This requires manual database editing - use full clear instead
```

### Force Re-execution
```bash
# Method 1: Clear state then run
rm -rf conversations/pipeline_state
python cli.py phone-discovery

# Method 2: Use complete pipelines (they handle dependencies)
python cli.py phone-pipeline
```

## 🛠️ Troubleshooting

### Stage Failures

**If a stage fails**:
1. Check the error message in console output
2. Review logs for detailed error information
3. Clear pipeline state to retry: `rm -rf conversations/pipeline_state`
4. Run the stage again

**Common Issues**:

**Phone Discovery Fails**:
```bash
# Check processing directory exists and contains HTML files
ls -la ../gvoice-convert/
ls -la ../gvoice-convert/Calls/ | head -5

# Clear state and retry
rm -rf conversations/pipeline_state
python cli.py phone-discovery
```

**Phone Lookup Fails**:
```bash
# Ensure phone discovery completed first
python cli.py phone-discovery

# Then run lookup
python cli.py phone-lookup --provider manual
```

**Content Extraction Fails**:
```bash
# Check file discovery completed
python cli.py file-discovery

# Try smaller batch size
python cli.py content-extraction --max-files 100
```

### Debugging Commands

**Check pipeline status**:
```bash
# View pipeline state database (requires sqlite3)
sqlite3 conversations/pipeline_state/pipeline_state.db "SELECT * FROM stage_executions ORDER BY execution_start DESC LIMIT 10;"
```

**View stage outputs**:
```bash
# Check phone discovery results
head -20 conversations/phone_inventory.json

# Check file discovery results  
head -20 conversations/file_inventory.json

# Check unknown numbers export
head -10 conversations/unknown_numbers.csv
```

### Recovery Procedures

**Complete Pipeline Reset**:
```bash
# Remove all pipeline state and outputs
rm -rf conversations/pipeline_state
rm -f conversations/phone_inventory.json
rm -f conversations/phone_directory.sqlite
rm -f conversations/unknown_numbers.csv
rm -f conversations/file_inventory.json
rm -f conversations/extracted_content.json

# Start fresh
python cli.py phone-pipeline
python cli.py file-pipeline
```

**Partial Reset** (reset specific stage):
```bash
# Reset phone processing only
rm -rf conversations/pipeline_state
rm -f conversations/phone_inventory.json
rm -f conversations/phone_directory.sqlite
rm -f conversations/unknown_numbers.csv

python cli.py phone-pipeline
```

## 📊 Understanding Output

### Phone Inventory Format
```json
{
  "discovery_metadata": {
    "scan_date": "2025-09-27T20:31:12Z",
    "processing_dir": "/path/to/gvoice-convert",
    "html_files_processed": 61484
  },
  "discovered_numbers": ["+1234567890", "+1555123456", ...],
  "known_numbers": ["+1234567890", ...],
  "unknown_numbers": ["+1555123456", ...],
  "discovery_stats": {
    "total_discovered": 9046,
    "known_count": 407,
    "unknown_count": 8639
  }
}
```

### File Inventory Format
```json
{
  "files": [
    {
      "path": "/full/path/to/file.html",
      "relative_path": "Calls/file.html",
      "type": "calls",
      "directory": "Calls",
      "size_bytes": 2048,
      "modified_time": "2025-09-27T20:31:12Z",
      "has_messages": true,
      "estimated_message_count": 5
    }
  ],
  "summary": {
    "total_files": 62314,
    "by_type": {"calls": 61484, "sms_mms": 830},
    "total_size_bytes": 203423744
  }
}
```

### Phone Directory Database Schema
```sql
-- SQLite database structure
CREATE TABLE phone_directory (
    phone_number TEXT PRIMARY KEY,
    display_name TEXT,
    source TEXT,              -- 'manual', 'api', 'carrier'
    is_spam BOOLEAN,
    spam_confidence REAL,
    line_type TEXT,           -- 'mobile', 'landline', 'voip'
    carrier TEXT,
    location TEXT,
    lookup_date TIMESTAMP,
    api_provider TEXT,
    api_response TEXT         -- JSON blob for audit trail
);
```

## 🔗 Integration with Original Workflow

The pipeline stages are **completely compatible** with the original conversion workflow:

```bash
# Recommended workflow for new users
python cli.py phone-pipeline      # Analyze phone numbers
python cli.py file-pipeline       # Analyze file structure
python cli.py convert             # Perform final conversion

# Traditional workflow (still works perfectly)
python cli.py --full-run convert

# Mixed workflow
python cli.py phone-discovery     # Get phone insights
python cli.py --test-mode convert # Test conversion with insights
python cli.py --full-run convert  # Full conversion
```

## 🎯 Best Practices

### For Large Datasets (50K+ files)
```bash
# Use smaller batch sizes for content extraction
python cli.py file-pipeline --max-files 1000

# Monitor memory usage during processing
python cli.py phone-pipeline
```

### For Development/Testing
```bash
# Always test with small datasets first
python cli.py --test-mode phone-discovery
python cli.py --test-mode file-discovery
python cli.py --test-mode --test-limit 10 convert
```

### For Production Use
```bash
# Run complete analysis first
python cli.py phone-pipeline --api ipqualityscore --api-key YOUR_KEY
python cli.py file-pipeline

# Review results before conversion
cat conversations/unknown_numbers.csv
head conversations/file_inventory.json

# Perform conversion
python cli.py --full-run convert
```

## 🔧 Advanced Usage

### API Integration
```bash
# IPQualityScore integration (requires API key)
python cli.py phone-lookup --provider ipqualityscore --api-key YOUR_KEY

# Export unknown numbers for manual research
python cli.py phone-lookup --provider manual --export-unknown my_numbers.csv
```

### Custom Processing
```bash
# Process only specific file types by running stages individually
python cli.py file-discovery
# Edit file_inventory.json to remove unwanted files
python cli.py content-extraction
```

### Batch Processing
```bash
# Process large datasets in smaller chunks
python cli.py content-extraction --max-files 500
# Wait for completion, then run again (will process next batch)
python cli.py content-extraction --max-files 500
```

This pipeline architecture provides powerful flexibility while maintaining full compatibility with existing workflows. Use individual stages for analysis and debugging, or complete pipelines for comprehensive processing.
