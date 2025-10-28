# Conversation Filtering System

Post-processor for filtering spam, commercial, political, and automated conversations from generated HTML files while protecting important communications through keyword matching.

## Overview

The conversation filtering system provides intelligent filtering of non-personal conversations using 15 tiered filtering patterns combined with a keyword protection safety net. This allows aggressive filtering while guaranteeing that legally-relevant or personally important conversations are never archived.

### Key Features

- **Protected-First Architecture**: Keyword protection evaluated BEFORE any filtering
- **15 Tiered Filtering Patterns**: Confidence scores from 0.75 to 0.98
- **Dry-Run Mode**: Preview changes before applying them
- **Generic & Reusable**: Keyword categories customizable for any use case
- **Reversible**: Archived files renamed with `.archived.html` extension
- **Index Integration**: Archived conversations automatically excluded from index.html

## Quick Start

### 1. Create Protected Keywords File

Create `protected_keywords.json` in your project root:

```json
{
  "description": "Protected keywords - conversations matching ANY keyword are protected from archiving",
  "case_sensitive": false,
  "match_partial": true,

  "keywords": {
    "important_people": [
      "John Doe",
      "Jane Smith",
      "Acme Corporation"
    ],
    "financial": [
      "$50,000",
      "invoice",
      "contract"
    ],
    "locations": [
      "123 Main Street",
      "Conference Room A"
    ]
  },

  "regex_patterns": [
    "INV\\d{4,}",
    "\\$\\d{4,}"
  ]
}
```

### 2. Run Dry-Run Preview

```bash
# Preview what would be archived (safe, no changes)
python cli.py filter-conversations
```

### 3. Apply Filtering

```bash
# Actually archive conversations
python cli.py filter-conversations --no-dry-run
```

### 4. Review Results

Check the summary output:

```
============================================================
📊 Filtering Summary
============================================================
   Total conversations: 873
   🔒 Protected by keywords: 78 (8.9%)
   📦 Archived: 647 (74.1%)
   ✅ Kept: 148 (17.0%)

📋 Top Archive Reasons:
   - Short-lived conversation (<1 hour): 304 conversations
   - One-way broadcast (no user replies): 92 conversations
   - STOP-only orphan message: 76 conversations
```

## Architecture

### Protected-First Flow

```
┌─────────────────────────────────┐
│  Parse Conversation HTML File  │
└───────────┬─────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│  Check Keyword Protection       │ ◄── STEP 1 (Always First!)
│  (protected_keywords.json)      │
└───────────┬─────────────────────┘
            │
            ├─── Match Found ───► 🔒 PROTECTED (Never Archive)
            │
            ▼ No Match
┌─────────────────────────────────┐
│  Run 15 Filtering Patterns      │ ◄── STEP 2 (Only if not protected)
│  (Confidence: 0.75 - 0.98)      │
└───────────┬─────────────────────┘
            │
            ├─── Should Archive ──► 📦 ARCHIVE (Rename to .archived.html)
            │
            ▼ Keep
            ✅ KEPT (No action)
```

### Component Architecture

```
┌──────────────────────────────────────────────────┐
│  filter-conversations CLI Command                │
│  (cli.py)                                        │
└────────────┬─────────────────────────────────────┘
             │
             ├──► HTMLConversationParser
             │    Parse HTML → Extract Messages
             │
             ├──► KeywordProtection
             │    Load keywords → Check protection
             │
             ├──► ConversationFilter
             │    Apply 15 patterns → Return decision
             │
             └──► File Rename (.archived.html)
```

## Filtering Patterns

### Very Safe Patterns (0.95-0.98 Confidence)

**Pattern 1: 2FA/Verification Codes (0.98)**
- Matches: "Your verification code is 123456", "2FA code: 789012"
- Keywords: `verification code`, `2fa code`, `otp`, `security code`

**Pattern 2: Delivery Notifications (0.97)**
- Matches: DoorDash, UberEats, package delivery notifications
- Detects: 50+ messages with 0 user replies
- Keywords: `order has been picked up`, `dasher is on the way`

**Pattern 3: STOP-Only Messages (0.96)**
- Matches: Single message conversations with only "STOP", "UNSUBSCRIBE"
- Example: One message: "Stop"

**Pattern 4: Appointment Reminders (0.95)**
- Matches: Medical appointments, service reminders
- Keywords: `appointment reminder`, `confirm your appointment`

**Pattern 5: Banking/Financial Alerts (0.95)**
- Matches: Account balance alerts, transaction notifications
- Keywords: `account balance`, `transaction alert`, `low balance`

### Safe Patterns (0.85-0.94 Confidence)

**Pattern 6: Political Campaigns (0.92)**
- Matches: Campaign donation requests, political surveys
- Keywords: `donate`, `700% match`, `endorse`, `vote for`
- Example: "HUGE 700% MATCH to stand with Kamala"

**Pattern 7: Marketing Promotions (0.90)**
- Matches: Flash sales, discount offers
- Keywords: `flash sale`, `limited time offer`, `50% off`

**Pattern 8: Medical Billing (0.88)**
- Matches: Toll-free numbers (800, 888, 866, 877, 855) + billing keywords
- Keywords: `bill is ready`, `statement available`

**Pattern 9: Surveys/Polls (0.87)**
- Matches: Customer satisfaction surveys, opinion polls
- Keywords: `live survey`, `take our poll`, `rate your experience`

**Pattern 10: Template Messages (0.85)**
- Matches: Conversations with >50% identical messages
- Example: 10 messages, 8 are identical copies

### Aggressive Patterns (0.75-0.84 Confidence)

**Pattern 11: One-Way Broadcast (0.82)**
- Matches: 3+ messages from sender, 0 user replies
- Example: All messages from company, no responses

**Pattern 12: Short-Lived Conversation (0.80)**
- Matches: 1-2 messages within 1 hour span
- Example: Quick exchange that didn't continue

**Pattern 13: Link-Heavy Messages (0.78)**
- Matches: >75% of messages contain URLs
- Example: Marketing messages with tracking links

**Pattern 14: No Alias + Commercial Keywords (0.76)**
- Matches: Unknown numbers with commercial terms
- Keywords: `unsubscribe`, `customer service`, `automated message`

**Pattern 15: No-Reply Pattern (0.75)**
- Matches: Messages indicating automated sending
- Keywords: `do not reply`, `noreply`, `automated message`

## Keyword Protection

### Configuration File: `protected_keywords.json`

The keyword protection file uses a flexible, category-based structure:

```json
{
  "description": "Protected keywords - conversations matching ANY keyword are protected from archiving",
  "last_updated": "2025-10-26",
  "case_sensitive": false,
  "match_partial": true,

  "keywords": {
    "category_name_1": [
      "Keyword 1",
      "Keyword 2"
    ],
    "category_name_2": [
      "Keyword 3"
    ]
  },

  "regex_patterns": [
    "pattern1",
    "pattern2"
  ],

  "notes": {
    "usage": "Any conversation matching ANY keyword in any category is protected from archiving",
    "editing": "Add new keywords to appropriate category, or create new categories as needed",
    "regex": "Regex patterns require escaping backslashes (\\d for digits, \\$ for dollar sign)",
    "case_sensitivity": "Set to false - matches 'keyword', 'KEYWORD', etc.",
    "partial_matching": "Set to true - 'Keyword Inc' matches 'Keyword'",
    "categories": "Category names are user-defined and can be customized for any use case"
  }
}
```

### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `case_sensitive` | boolean | Match case exactly (default: `false`) |
| `match_partial` | boolean | Allow partial matches (default: `true`) |
| `keywords` | object | Category-organized keyword lists |
| `regex_patterns` | array | Regular expression patterns for advanced matching |

### Category Organization

Categories are **user-defined** and can be customized for any use case:

```json
{
  "keywords": {
    "legal_case_names": ["Doe v. Smith", "Case #12345"],
    "project_names": ["Project Phoenix", "Alpha Initiative"],
    "important_dates": ["November 8, 2024", "Q4 2024"],
    "financial_terms": ["Series A", "acquisition", "$500k"],
    "locations": ["headquarters", "Building 3", "Conference Room"],
    "people_leadership": ["CEO", "Board Member"],
    "custom_category": ["Any", "Keywords", "You", "Need"]
  }
}
```

### Regex Pattern Examples

```json
{
  "regex_patterns": [
    "INV\\d{4,}",              // Invoice numbers: INV1234, INV56789
    "CO\\d+",                  // Change orders: CO1, CO42
    "\\$\\d{4,}",             // Dollar amounts: $1000, $50000
    "[A-Z]{3}-\\d{3}",        // Codes: ABC-123, XYZ-789
    "\\b\\d{3}-\\d{2}-\\d{4}\\b"  // SSN format (BE CAREFUL!)
  ]
}
```

**Important**: Regex patterns require escaping backslashes in JSON:
- `\d` → `\\d`
- `\$` → `\\$`
- `\.` → `\\.`

## CLI Usage

### Command Options

```bash
python cli.py [GLOBAL_OPTIONS] filter-conversations [COMMAND_OPTIONS]
```

### Global Options (Before command name)

```bash
--processing-dir PATH    # Directory with conversations/ folder
                        # Default: ../gvoice-convert
```

### Command Options (After command name)

| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` / `--no-dry-run` | `--dry-run` | Preview mode (no changes) |
| `--keywords-file PATH` | `protected_keywords.json` | Path to keyword protection file |
| `--min-confidence FLOAT` | `0.75` | Minimum confidence score (0.0-1.0) |
| `--show-protected` | `False` | Show protected conversations in output |
| `--show-kept` | `False` | Show kept conversations in output |

### Examples

**Basic dry-run (preview only):**
```bash
python cli.py filter-conversations
```

**With custom processing directory:**
```bash
python cli.py --processing-dir /path/to/conversations filter-conversations
```

**Actually archive conversations:**
```bash
python cli.py filter-conversations --no-dry-run
```

**Use custom keywords file:**
```bash
python cli.py filter-conversations --keywords-file my_keywords.json
```

**Adjust confidence threshold (more aggressive filtering):**
```bash
python cli.py filter-conversations --min-confidence 0.70
```

**Show all conversation types:**
```bash
python cli.py filter-conversations --show-protected --show-kept
```

**Combine options:**
```bash
python cli.py --processing-dir ~/my-data filter-conversations \
  --no-dry-run \
  --keywords-file legal_keywords.json \
  --min-confidence 0.80 \
  --show-protected
```

## Output & Results

### Dry-Run Output

```
🔍 Starting conversation filtering...
   [DRY RUN]
   Conversations dir: /Users/you/conversations
   Min confidence: 0.75
   ✅ Keyword protection enabled:
      - Keywords: 94
      - Patterns: 4
      - Categories: 11
   ✅ Phone lookup loaded: 442 aliases

📊 Found 873 conversation files to process

   📦 ARCHIVE: +12025948401.html
      Reason: STOP-only orphan message
      Confidence: 0.96
      Messages: 1

   📦 ARCHIVE: +12056277344.html
      Reason: High volume automated delivery notifications
      Confidence: 0.97
      Messages: 400

============================================================
📊 Filtering Summary
============================================================
   Total conversations: 873
   🔒 Protected by keywords: 78 (8.9%)
   📦 Archived: 647 (74.1%)
   ✅ Kept: 148 (17.0%)

💡 This was a DRY RUN - no files were modified
   Run with --no-dry-run to actually archive conversations

📋 Top Archive Reasons:
   - Short-lived conversation (<1 hour): 304 conversations
   - One-way broadcast (no user replies): 92 conversations
   - STOP-only orphan message: 76 conversations
   - Political campaign pattern: 76 conversations
   - 2FA/verification code pattern: 37 conversations
```

### Live Mode Output

When run with `--no-dry-run`:

```
   📦 ARCHIVE: +12025948401.html
      Reason: STOP-only orphan message
      Confidence: 0.96
      Messages: 1
      ✅ Renamed to: +12025948401.archived.html

✅ Conversations have been archived (renamed to .archived.html)
   To restore, rename .archived.html files back to .html
```

## File Organization

### Before Filtering

```
conversations/
├── index.html
├── Alice.html                 # Personal conversation
├── Bob.html                   # Protected by keyword
├── +12025948401.html         # Spam (will archive)
├── +12056277344.html         # Delivery spam (will archive)
└── Mike_Daddio.html          # Protected by keyword
```

### After Filtering

```
conversations/
├── index.html                 # Updated (excludes .archived.html)
├── Alice.html                 # Kept (real conversation)
├── Bob.html                   # Kept (protected by keyword)
├── +12025948401.archived.html # Archived (STOP message)
├── +12056277344.archived.html # Archived (delivery spam)
└── Mike_Daddio.html          # Kept (protected by keyword)
```

**Note**: `index.html` automatically excludes `.archived.html` files from the conversation list.

## Restoring Archived Conversations

### Restore Individual Files

```bash
# Rename back to .html
mv +12025948401.archived.html +12025948401.html
```

### Restore All Archived Files

```bash
# macOS/Linux
cd conversations/
for file in *.archived.html; do
  mv "$file" "${file%.archived.html}.html"
done

# Windows PowerShell
cd conversations
Get-ChildItem *.archived.html | Rename-Item -NewName {$_.Name -replace '.archived.html$','.html'}
```

### Regenerate Index

After restoring files, regenerate the index to include them:

```bash
python cli.py index-generation
```

## Creating Distribution Tarballs

### Overview

After filtering conversations, you can create a clean, self-contained tarball for external sharing (e.g., sending to lawyers, archiving for long-term storage, sharing with collaborators).

The `create-distribution-tarball` command creates a compressed archive containing:

- ✅ All conversations referenced in `index.html`
- ✅ All attachments referenced by those conversations
- ❌ **Excludes** `.archived.html` files (filtered spam/commercial conversations)
- ❌ **Excludes** orphaned attachments (not referenced by any conversation)

### Use Case

**Scenario**: You've processed 60,000+ Google Voice messages, filtered out spam, and need to send a clean archive to your lawyer.

**Problem**: Your `conversations/` directory contains:
- 873 conversation HTML files (148 legitimate, 725 archived spam)
- 1,200 attachments (some orphaned, some referenced by archived conversations)
- Archived `.archived.html` files mixed in with legitimate conversations

**Solution**: `create-distribution-tarball` packages **only** the legitimate conversations and their attachments into a single, clean `.tar.gz` file.

### Basic Usage

```bash
# Step 1: Filter spam conversations
python cli.py filter-conversations --no-dry-run

# Step 2: Regenerate index (excludes archived conversations)
python cli.py --filter-non-phone-numbers --no-include-call-only-conversations html-generation
python cli.py index-generation

# Step 3: Create distribution tarball
python cli.py create-distribution-tarball
```

This creates `distribution.tar.gz` in your processing directory.

### Command Options

```bash
python cli.py [GLOBAL_OPTIONS] create-distribution-tarball [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output PATH` | `distribution.tar.gz` | Output tarball filename |
| `--verify` / `--no-verify` | `--verify` | Verify tarball contents after creation |

### Examples

**Basic usage (default output):**
```bash
python cli.py create-distribution-tarball
# Creates: distribution.tar.gz
```

**Custom output filename:**
```bash
python cli.py create-distribution-tarball --output lawyers_archive_2024.tar.gz
# Creates: lawyers_archive_2024.tar.gz
```

**With custom processing directory:**
```bash
python cli.py --processing-dir ~/my-data create-distribution-tarball
```

**Skip verification (faster for large archives):**
```bash
python cli.py create-distribution-tarball --no-verify
```

**Combine options:**
```bash
python cli.py --processing-dir ~/gvoice-data create-distribution-tarball \
  --output legal_archive_q4_2024.tar.gz \
  --verify
```

### Output Example

```
📋 Step 1: Extracting conversations from index.html...
   ✅ Found 148 conversations

📎 Step 2: Extracting attachments from conversations...
   ✅ Found 237 unique attachments

📦 Step 3: Creating tarball: legal_archive.tar.gz...
   ✅ Created: /Users/you/gvoice-convert/legal_archive.tar.gz
   📊 Size: 45.23 MB

🔍 Step 4: Verifying tarball contents...
   ✅ index.html present
   ✅ No .archived.html files (clean)
   ✅ 148 conversations
   ✅ 237 attachments
   ✅ 386 total files

============================================================
✅ SUCCESS: Distribution tarball created
============================================================
Output: /Users/you/gvoice-convert/legal_archive.tar.gz
Size: 45.23 MB
Conversations: 148
Attachments: 237

💡 Tip: Extract with: tar -xzf legal_archive.tar.gz
```

### Tarball Structure

The tarball maintains the original directory structure:

```
legal_archive.tar.gz
└── conversations/
    ├── index.html
    ├── Alice.html
    ├── Bob.html
    ├── Mike_Daddio.html
    └── attachments/
        ├── photo1.jpg
        ├── photo2.jpg
        └── document.pdf
```

**What's NOT included:**
- `+12025948401.archived.html` (spam conversation)
- `orphaned_attachment.jpg` (not referenced by any conversation)
- `.gvoice_cache/` (metadata cache)
- `pipeline_state/` (processing state)

### Extracting the Tarball

**macOS/Linux:**
```bash
tar -xzf distribution.tar.gz
```

**Windows:**
```powershell
# Using tar (Windows 10+)
tar -xzf distribution.tar.gz

# Using 7-Zip
7z x distribution.tar.gz
```

**Extract to specific directory:**
```bash
tar -xzf distribution.tar.gz -C /path/to/destination
```

### Verification

The `--verify` flag (enabled by default) performs these checks:

1. ✅ `index.html` is present
2. ✅ No `.archived.html` files in tarball
3. ✅ Conversation count matches expectations
4. ✅ Attachment count matches expectations
5. ✅ Total file count

**Example verification output:**
```
🔍 Step 4: Verifying tarball contents...
   ✅ index.html present
   ✅ No .archived.html files (clean)
   ✅ 148 conversations
   ✅ 237 attachments
   ✅ 386 total files
```

If verification finds issues, warnings are displayed:

```
   ⚠️  WARNING: index.html not in tarball
   ⚠️  WARNING: 3 .archived.html files found in tarball
```

### Complete Workflow

Here's the recommended end-to-end workflow for creating a clean distribution:

```bash
# 1. Process raw Google Voice Takeout export
python cli.py attachment-mapping
python cli.py attachment-copying
python cli.py --filter-non-phone-numbers --no-include-call-only-conversations html-generation
python cli.py index-generation

# 2. Review conversations and filter spam
python cli.py filter-conversations                    # Dry-run preview
python cli.py filter-conversations --no-dry-run       # Apply filtering

# 3. Regenerate index to exclude archived conversations
python cli.py index-generation

# 4. Create clean distribution tarball
python cli.py create-distribution-tarball --output lawyers_archive.tar.gz

# 5. Verify the tarball was created correctly
ls -lh lawyers_archive.tar.gz
```

### Troubleshooting

**Error: "Conversations directory not found"**

```
❌ Conversations directory not found: /path/to/conversations
   Run 'python cli.py html-generation' first to generate conversations
```

**Solution**: Generate conversations first using the pipeline:
```bash
python cli.py html-generation
python cli.py index-generation
```

---

**Error: "index.html not found"**

```
❌ index.html not found: /path/to/conversations/index.html
   Run 'python cli.py index-generation' first
```

**Solution**: Generate index.html:
```bash
python cli.py index-generation
```

---

**Warning: ".archived.html files found in tarball"**

```
⚠️  WARNING: 3 .archived.html files found in tarball
```

**Solution**: Regenerate index.html after filtering to exclude archived conversations:
```bash
python cli.py index-generation
python cli.py create-distribution-tarball
```

---

**Tarball contains orphaned attachments**

This is expected behavior. The command only includes attachments **referenced by conversations in index.html**. Orphaned attachments are automatically excluded.

To verify attachment count:
```bash
tar -tzf distribution.tar.gz | grep attachments/ | wc -l
```

### Best Practices

**1. Always filter before creating tarball:**
```bash
# ✅ Good workflow
python cli.py filter-conversations --no-dry-run
python cli.py index-generation
python cli.py create-distribution-tarball

# ❌ Skip filtering = tarball includes spam
python cli.py create-distribution-tarball
```

**2. Use descriptive filenames:**
```bash
# ✅ Good: Descriptive, dated
python cli.py create-distribution-tarball --output legal_archive_2024_q4.tar.gz

# ❌ Ambiguous
python cli.py create-distribution-tarball --output archive.tar.gz
```

**3. Verify large tarballs:**
```bash
# For large archives (>1GB), verification adds ~5-10 seconds
python cli.py create-distribution-tarball --verify
```

**4. Keep original conversations directory:**

The tarball creation is **non-destructive** - original files remain unchanged. Keep your `conversations/` directory as the source of truth.

## Integration with Pipeline

The conversation filtering and distribution system integrates with the existing pipeline:

```
Phase 1: attachment-mapping           → Build attachment catalog
Phase 2: attachment-copying           → Copy attachments to output
Phase 3: html-generation              → Generate conversation HTML files
Phase 4: index-generation             → Generate index.html

[NEW] Post-Process 1: filter-conversations        → Archive spam/commercial conversations
                                                  → Protected-first architecture
                                                  → Archived files excluded from index

[NEW] Post-Process 2: create-distribution-tarball → Package clean conversations
                                                  → Include only index-referenced files
                                                  → Exclude archived conversations
                                                  → Ready for external sharing
```

**Recommended workflow:**

```bash
# 1. Generate conversations
python cli.py html-generation

# 2. Generate initial index
python cli.py index-generation

# 3. Filter spam (dry-run first!)
python cli.py filter-conversations

# 4. Apply filtering
python cli.py filter-conversations --no-dry-run

# 5. Regenerate index (excludes archived files)
python cli.py index-generation

# 6. Create distribution tarball
python cli.py create-distribution-tarball --output clean_archive.tar.gz
```

## Troubleshooting

### No conversations being archived

**Cause**: All conversations might be protected by keywords
**Solution**: Review `protected_keywords.json` - may be too broad

```bash
# Show protected conversations
python cli.py filter-conversations --show-protected
```

### Too many conversations being archived

**Cause**: Minimum confidence too low or keywords too narrow
**Solution**: Adjust `--min-confidence` or add more keywords

```bash
# Increase confidence threshold (less aggressive)
python cli.py filter-conversations --min-confidence 0.85

# Show what would be kept
python cli.py filter-conversations --show-kept
```

### Keyword protection not working

**Check keyword file location:**
```bash
# Should be in project root or conversations/ directory
ls protected_keywords.json
ls conversations/protected_keywords.json
```

**Validate JSON syntax:**
```bash
python -m json.tool protected_keywords.json
```

**Check keyword matching:**
- `case_sensitive: false` → Matches "Mike Daddio", "MIKE DADDIO", "mike daddio"
- `match_partial: true` → "Mike Daddio Inc" matches "Mike Daddio"
- `match_partial: false` → Requires exact word match

### Parse errors

**Symptom**: `❌ ERROR: filename.html: ...`

**Causes**:
- Malformed HTML file
- Corrupted file
- Non-standard HTML structure

**Solution**: Check the specific file, may need manual review

## Performance

### Benchmark Results

Test dataset: 873 conversation files

| Operation | Time | Rate |
|-----------|------|------|
| Parse all files | ~8 seconds | 109 files/sec |
| Apply all filters | ~2 seconds | 436 files/sec |
| **Total filtering** | **~10 seconds** | **87 files/sec** |

**Memory usage**: < 50 MB for 873 conversations

**Scalability**: Linear O(n) - tested up to 10,000 conversations

## Advanced Usage

### Custom Confidence Thresholds by Pattern

You can manually edit `core/conversation_filter.py` to adjust confidence scores:

```python
# Make pattern more aggressive (lower confidence)
return True, "Political campaign pattern", 0.85  # Was 0.92

# Make pattern safer (higher confidence)
return True, "Short-lived conversation", 0.88  # Was 0.80
```

### Adding New Filtering Patterns

1. Edit `core/conversation_filter.py`
2. Add new pattern method following existing structure:

```python
def _check_custom_pattern(
    self,
    messages: List[Dict[str, Any]]
) -> Optional[Tuple[bool, str, float]]:
    """
    Pattern 16: Your custom pattern (0.XX confidence)

    Matches:
    - Description of what this pattern matches
    """
    # Your filtering logic here
    if condition_met:
        return True, "Custom pattern description", 0.85

    return None
```

3. Call pattern in `should_archive_conversation()`:

```python
# Add after existing patterns
result = self._check_custom_pattern(messages)
if result:
    return result
```

### Batch Processing Multiple Datasets

```bash
# Process multiple conversation directories
for dir in dataset1 dataset2 dataset3; do
  python cli.py --processing-dir "$dir" filter-conversations --no-dry-run
done
```

## API Reference

### Core Classes

#### `KeywordProtection`

```python
from core.keyword_protection import KeywordProtection

# Initialize
protection = KeywordProtection(Path("protected_keywords.json"))

# Check if protected
is_protected, keyword = protection.is_protected(messages)

# Get stats
stats = protection.get_stats()
# Returns: {'total_keywords': 94, 'total_patterns': 4, ...}

# Test individual text
is_protected, keyword = protection.test_keyword("Call Mike Daddio")
```

#### `ConversationFilter`

```python
from core.conversation_filter import ConversationFilter

# Initialize
filter = ConversationFilter(keyword_protection)

# Evaluate conversation
should_archive, reason, confidence = filter.should_archive_conversation(
    messages=[{'text': 'STOP', 'sender': 'Me', 'timestamp': 1234567890000}],
    sender_phone='+12025948401',
    has_alias=False
)

# Get filter stats
stats = filter.get_stats()
# Returns: {'total_patterns': 15, 'very_safe_patterns': 5, ...}
```

#### `HTMLConversationParser`

```python
from core.html_conversation_parser import HTMLConversationParser

# Initialize
parser = HTMLConversationParser()

# Parse single file
data = parser.parse_conversation_file(Path("Alice.html"))
# Returns: {'conversation_id': 'Alice', 'messages': [...], ...}

# Batch parse
conversations = parser.parse_batch([path1, path2, path3])
```

## Best Practices

### 1. Always Dry-Run First

Never run `--no-dry-run` without previewing:

```bash
# ✅ Good
python cli.py filter-conversations                    # Preview
python cli.py filter-conversations --no-dry-run       # Apply

# ❌ Bad
python cli.py filter-conversations --no-dry-run       # Applied without review!
```

### 2. Start with Higher Confidence

For conservative filtering, start with higher confidence:

```bash
# Very conservative (only very safe patterns)
python cli.py filter-conversations --min-confidence 0.90

# Balanced (default)
python cli.py filter-conversations --min-confidence 0.75

# Aggressive (includes more patterns)
python cli.py filter-conversations --min-confidence 0.70
```

### 3. Maintain Keyword File

Keep your keyword file updated as you discover new important terms:

```json
{
  "keywords": {
    "people_new_contractors": [
      "New Contractor Name",
      "Another Person"
    ]
  }
}
```

### 4. Review Top Archive Reasons

Check if patterns align with your expectations:

```
📋 Top Archive Reasons:
   - Short-lived conversation (<1 hour): 304 conversations
```

If a pattern is too aggressive, increase `--min-confidence`.

### 5. Test on Subset First

Test on a small subset before full run:

```bash
# Filter only archived conversations manually
mkdir test_subset
cp conversations/{+1234567890,+0987654321}.html test_subset/

# Test on subset
python cli.py --processing-dir test_subset filter-conversations
```

## Security & Privacy

### Keyword File Security

The keyword file may contain sensitive information:

- **Never commit to public repositories**
- Add to `.gitignore`:
  ```
  protected_keywords.json
  *_keywords.json
  ```
- Store in secure location
- Use file permissions:
  ```bash
  chmod 600 protected_keywords.json
  ```

### Archived File Management

Archived files are **not deleted**, only renamed:

- Still contain original content
- Still accessible in `conversations/` directory
- Not removed from disk
- To permanently delete:
  ```bash
  rm conversations/*.archived.html
  ```

## FAQ

**Q: Can I filter during HTML generation instead of post-processing?**

A: Yes, but post-processing is recommended:
- Allows review before archiving
- Non-destructive (reversible)
- Can adjust filters without regenerating
- Protected-first architecture easier to implement

**Q: What happens if I run filter-conversations twice?**

A: Archived files are skipped (`.archived.html` excluded from glob pattern), so it's safe to run multiple times.

**Q: Can I use multiple keyword files?**

A: Currently supports one file. To merge multiple files, combine keyword categories into single JSON.

**Q: How do I see which keywords protected a conversation?**

A: Use `--show-protected`:
```bash
python cli.py filter-conversations --show-protected
```

Output shows matched keyword:
```
🔒 PROTECTED: Mike_Daddio.html
   Reason: Protected: matches 'Mike Daddio'
```

**Q: Can I archive by date range?**

A: Not currently built in, but you can filter during html-generation:
```bash
python cli.py --include-date-range 2020-01-01_2024-12-31 html-generation
```

**Q: What if I want to restore all archived conversations?**

A: See "Restoring Archived Conversations" section above.

## Version History

### v1.0.0 (2025-10-26)

**Initial Release**

- 15 tiered filtering patterns (0.75-0.98 confidence)
- Protected-first keyword matching architecture
- Category-based keyword organization
- Regex pattern support
- Dry-run mode
- CLI integration
- Index generation integration
- Comprehensive documentation

**Test Results:**
- 873 conversations processed
- 78 (8.9%) protected by keywords
- 647 (74.1%) archived as spam/commercial
- 148 (17.0%) kept as personal conversations
- Processing time: ~10 seconds

## Support & Contributing

### Reporting Issues

Include in your report:
- Command used
- Dry-run output
- Excerpt from protected_keywords.json
- Example conversation that was incorrectly filtered

### Feature Requests

Suggestions for new filtering patterns:
- Describe pattern characteristics
- Provide example messages
- Suggest confidence score
- Explain use case

## License

Part of Google Voice SMS Takeout HTML Converter project. Same license applies.
