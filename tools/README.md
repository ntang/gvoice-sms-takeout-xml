# Phone Number Analysis Tools

This directory contains analysis tools for the Google Voice SMS Takeout phone number filtering project.

## Tools Overview

### 1. `clean_phone_analysis.py`
**Purpose**: Comprehensive analysis of unknown phone numbers using corrected pipeline data
**Status**: ✅ Working - Built on post-bug-fix data
**Results**: 
- 694 numbers with conversations (8.0%)
- 1,066 toll-free numbers identified
- 44 suspicious patterns detected
- Cost analysis and recommendations

### 2. `immediate_free_filtering.py`
**Purpose**: Filter toll-free and suspicious numbers from unknown_numbers.csv
**Status**: ✅ Working - Successfully filtered 1,099 numbers
**Results**:
- 1,066 toll-free numbers filtered
- 44 suspicious patterns filtered
- $10.99 cost savings
- Clean CSV exports generated

### 3. `name_based_conversation_linking.py`
**Purpose**: Link name-based conversation files to phone numbers using phone_lookup.txt
**Status**: ✅ Working - 98.7% match rate achieved
**Results**:
- 149/151 name-based files successfully linked
- 42 additional conversations discovered
- Enhanced frequency analysis completed

### 4. `analyze_no_conversation_numbers.py`
**Purpose**: Validate number formats and analyze zero-conversation numbers
**Status**: ✅ Working - All 8,634 numbers have valid formats
**Results**:
- No format bugs found
- 7,940 zero-conversation numbers analyzed
- Root cause analysis completed

### 5. `investigate_zero_conversations.py`
**Purpose**: Deep dive into why numbers have zero conversations (100 random sample)
**Status**: ✅ Working - Critical insights discovered
**Results**:
- 100% affected by date range filtering
- 14% already in phone_lookup.txt
- Conversation-based filtering identified as invalid

## Usage

All tools are designed to be run from the project root directory:

```bash
source env/bin/activate
python tools/[tool_name].py
```

## Dependencies

- Python 3.9+
- Virtual environment activated
- Clean pipeline data (post-bug-fix)
- Required data files in `../gvoice-convert/conversations/`

## Output Files

Tools generate various output files in the project root:
- `*_results.json` - Analysis results
- `filtered_*.csv` - Filtered number lists
- `remaining_*.csv` - Numbers for further analysis

## Data Quality

All tools are built on corrected data after the phone number normalization bug was fixed. They represent the current state of the analysis pipeline and provide accurate, actionable insights.
