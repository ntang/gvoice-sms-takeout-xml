# Phase 4 Enhancement Plan: Per-Conversation Statistics

**Date**: 2025-10-20
**Status**: 📋 **PLANNING**
**Complexity**: 🟢 **LOW-MEDIUM** - Straightforward enhancement to existing stages
**Estimated Effort**: 30-45 minutes

---

## Executive Summary

Currently, the index.html shows correct **summary statistics** (146,123 SMS, 30,346 calls, etc.) but **per-conversation statistics** are all zeros. This enhancement will:

1. **Phase 3a (HTML Generation)**: Store per-conversation stats during HTML generation
2. **Phase 4 (Index Generation)**: Load and display per-conversation stats in index table

**Goal**: Accurate per-conversation message counts in index.html table rows.

---

## Current Problem

### What Works ✅
- **Summary stats** at top of index.html are correct
- Stats loaded from `html_processing_state.json`
- Total counts: 146,123 SMS, 30,346 calls, 2,781 voicemails, 20,046 images, 23 vCards

### What's Broken ❌
- **Per-conversation stats** in table rows show all zeros
- Each conversation row shows: 0 SMS, 0 calls, 0 voicemails, 0 attachments

### Root Cause

**Phase 4's `_extract_file_metadata()` only reads file system metadata**:

```python
def _extract_file_metadata(self, file_path: Path) -> Dict:
    """Extract metadata from a conversation HTML file."""
    return {
        'file_path': file_path.name,
        'file_size': stat.st_size,
        'sms_count': 0,  # <-- HARDCODED ZERO!
        'call_count': 0,  # <-- HARDCODED ZERO!
        'voicemail_count': 0,  # <-- HARDCODED ZERO!
        'attachment_count': 0,  # <-- HARDCODED ZERO!
        'latest_message_timestamp': None,
        'last_modified': stat.st_mtime
    }
```

**Why**: Phase 4 doesn't have access to per-conversation statistics because Phase 3a never saved them.

---

## Solution Design

### Two-Stage Enhancement

#### Stage 1: Enhance Phase 3a (HTML Generation)
**What**: Store per-conversation statistics during HTML generation
**Where**: `core/pipeline/stages/html_generation.py`
**How**: Extend `html_processing_state.json` with per-conversation stats

#### Stage 2: Enhance Phase 4 (Index Generation)
**What**: Load per-conversation statistics from Phase 3a's state file
**Where**: `core/pipeline/stages/index_generation.py`
**How**: Replace `_extract_file_metadata()` with stat loading logic

---

## Data Structure Design

### Enhanced `html_processing_state.json`

**Current structure** (Phase 3a):
```json
{
  "files_processed": [
    "/Users/nicholastang/gvoice-convert/Calls/Group Conversation - 2023-04-16T21_04_03Z.html",
    ...
  ],
  "stats": {
    "num_sms": 146123,
    "num_img": 20046,
    "num_vcf": 23,
    "num_calls": 30346,
    "num_voicemails": 2781
  }
}
```

**Enhanced structure** (NEW):
```json
{
  "files_processed": [
    "/Users/nicholastang/gvoice-convert/Calls/Group Conversation - 2023-04-16T21_04_03Z.html",
    ...
  ],
  "stats": {
    "num_sms": 146123,
    "num_img": 20046,
    "num_vcf": 23,
    "num_calls": 30346,
    "num_voicemails": 2781
  },
  "conversations": {
    "Alice": {
      "sms_count": 234,
      "call_count": 12,
      "voicemail_count": 3,
      "attachment_count": 45,
      "latest_message_timestamp": "2024-10-18T19:04:55Z",
      "file_path": "Alice.html"
    },
    "Bob": {
      "sms_count": 156,
      "call_count": 8,
      "voicemail_count": 1,
      "attachment_count": 22,
      "latest_message_timestamp": "2024-10-19T10:30:00Z",
      "file_path": "Bob.html"
    },
    ...  // 6,847 conversations
  }
}
```

**New field**: `conversations` - Dictionary mapping conversation ID to statistics

**Why this structure**:
- ✅ **Minimal changes** to existing state file
- ✅ **Backward compatible** - old fields remain unchanged
- ✅ **Single source of truth** - all stats in one place
- ✅ **Fast lookups** - O(1) access by conversation ID

---

## Implementation Plan

### Part 1: Enhance Phase 3a (HTML Generation)

**File**: `core/pipeline/stages/html_generation.py`

**Changes**:

#### 1. Track Per-Conversation Stats During Processing

**Location**: Around line 140 (in `execute()` method)

**Current code**:
```python
# Process HTML files
result = process_html_files_param(
    processing_dir=context.processing_dir,
    html_files=files_to_process,
    context=processing_context,
    config=config
)

# Update statistics
state_data['stats']['num_sms'] += result['num_sms']
state_data['stats']['num_img'] += result['num_img']
...
```

**Enhanced code**:
```python
# Process HTML files
result = process_html_files_param(
    processing_dir=context.processing_dir,
    html_files=files_to_process,
    context=processing_context,
    config=config
)

# Update global statistics (existing)
state_data['stats']['num_sms'] += result['num_sms']
state_data['stats']['num_img'] += result['num_img']
...

# NEW: Extract per-conversation stats from ConversationManager
if 'conversations' not in state_data:
    state_data['conversations'] = {}

conversation_stats = self._extract_conversation_stats(processing_context.conversation_manager)
state_data['conversations'].update(conversation_stats)
```

#### 2. Add Helper Method to Extract Stats

**New method** (add after `execute()`):

```python
def _extract_conversation_stats(self, conversation_manager) -> Dict[str, Dict]:
    """
    Extract per-conversation statistics from ConversationManager.

    Args:
        conversation_manager: ConversationManager instance with buffered data

    Returns:
        Dictionary mapping conversation ID to statistics
    """
    stats = {}

    for conversation_id, buffer_data in conversation_manager.conversation_buffers.items():
        # Extract statistics from buffer
        stats[conversation_id] = {
            'sms_count': buffer_data.get('sms_count', 0),
            'call_count': buffer_data.get('call_count', 0),
            'voicemail_count': buffer_data.get('voicemail_count', 0),
            'attachment_count': buffer_data.get('attachment_count', 0),
            'latest_message_timestamp': buffer_data.get('latest_timestamp'),
            'file_path': f"{conversation_id}.html"
        }

    return stats
```

**Note**: Need to verify ConversationManager tracks these stats. If not, may need to enhance ConversationManager first.

---

### Part 2: Enhance Phase 4 (Index Generation)

**File**: `core/pipeline/stages/index_generation.py`

**Changes**:

#### 1. Load Per-Conversation Stats from Phase 3a

**Location**: In `_build_conversation_metadata()` method (around line 310)

**Current code**:
```python
def _build_conversation_metadata(self, conv_files: List[Path], cached_metadata: Dict) -> Dict:
    """Build metadata for all conversation files."""
    metadata = {}

    for file_path in conv_files:
        conversation_id = file_path.stem

        # Use cache if file hasn't been modified
        if cached_mtime and abs(float(cached_mtime) - current_mtime) < 1.0:
            metadata[conversation_id] = cached
        else:
            metadata[conversation_id] = self._extract_file_metadata(file_path)

    return metadata
```

**Enhanced code**:
```python
def _build_conversation_metadata(
    self,
    conv_files: List[Path],
    cached_metadata: Dict,
    conversation_stats: Dict  # NEW parameter
) -> Dict:
    """Build metadata for all conversation files."""
    metadata = {}

    for file_path in conv_files:
        conversation_id = file_path.stem

        # Use cache if file hasn't been modified
        if cached_mtime and abs(float(cached_mtime) - current_mtime) < 1.0:
            metadata[conversation_id] = cached
        else:
            # Extract file metadata (size, mtime)
            file_meta = self._extract_file_metadata(file_path)

            # Merge with per-conversation stats from Phase 3a
            conv_stats = conversation_stats.get(conversation_id, {})
            file_meta.update({
                'sms_count': conv_stats.get('sms_count', 0),
                'call_count': conv_stats.get('call_count', 0),
                'voicemail_count': conv_stats.get('voicemail_count', 0),
                'attachment_count': conv_stats.get('attachment_count', 0),
                'latest_message_timestamp': conv_stats.get('latest_message_timestamp')
            })

            metadata[conversation_id] = file_meta

    return metadata
```

#### 2. Update `execute()` to Pass Stats

**Location**: In `execute()` method (around line 195)

**Current code**:
```python
# Load statistics from HTML generation stage
html_state_file = context.output_dir / "html_processing_state.json"
stats = self._load_html_stats(html_state_file)

# Extract metadata for all files
metadata = self._build_conversation_metadata(
    conv_files,
    cached_metadata.get('conversations', {})
)
```

**Enhanced code**:
```python
# Load statistics from HTML generation stage
html_state_file = context.output_dir / "html_processing_state.json"
html_state = self._load_html_state(html_state_file)  # Load full state, not just stats
stats = html_state.get('stats', {})
conversation_stats = html_state.get('conversations', {})  # NEW

# Extract metadata for all files
metadata = self._build_conversation_metadata(
    conv_files,
    cached_metadata.get('conversations', {}),
    conversation_stats  # NEW parameter
)
```

#### 3. Add Helper Method to Load Full State

**New method** (replace `_load_html_stats()`):

```python
def _load_html_state(self, state_file: Path) -> Dict:
    """Load complete state from HTML processing state file."""
    if not state_file.exists():
        logger.warning("HTML processing state file not found - using empty state")
        return {
            'stats': {
                'num_sms': 0,
                'num_img': 0,
                'num_vcf': 0,
                'num_calls': 0,
                'num_voicemails': 0
            },
            'conversations': {}
        }

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)

            # Ensure conversations key exists
            if 'conversations' not in state:
                logger.warning("No per-conversation stats found in state file")
                state['conversations'] = {}

            return state
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load HTML state: {e}")
        return {
            'stats': {...},
            'conversations': {}
        }
```

---

## Testing Strategy

### Unit Tests (TDD)

**File**: `tests/unit/test_html_generation_stage.py` (NEW tests)

**New tests to add**:

```python
class TestPerConversationStats:
    """Test per-conversation statistics tracking."""

    def test_stores_per_conversation_stats(self, stage, context):
        """Should store per-conversation stats in state file."""
        # Execute stage
        result = stage.execute(context)

        # Load state file
        state_file = context.output_dir / "html_processing_state.json"
        with open(state_file) as f:
            state = json.load(f)

        # Verify conversations field exists
        assert 'conversations' in state
        assert len(state['conversations']) > 0

        # Verify structure
        for conv_id, conv_stats in state['conversations'].items():
            assert 'sms_count' in conv_stats
            assert 'call_count' in conv_stats
            assert 'voicemail_count' in conv_stats
            assert 'attachment_count' in conv_stats

    def test_conversation_stats_match_global_stats(self, stage, context):
        """Per-conversation stats should sum to global stats."""
        result = stage.execute(context)

        state_file = context.output_dir / "html_processing_state.json"
        with open(state_file) as f:
            state = json.load(f)

        # Sum per-conversation stats
        total_sms = sum(c.get('sms_count', 0) for c in state['conversations'].values())
        total_calls = sum(c.get('call_count', 0) for c in state['conversations'].values())

        # Should match global stats
        assert total_sms == state['stats']['num_sms']
        assert total_calls == state['stats']['num_calls']
```

**File**: `tests/unit/test_index_generation_stage.py` (UPDATE existing tests)

**Tests to update**:

```python
class TestExecution:
    def test_loads_per_conversation_stats(self, stage, context, sample_conversations):
        """Should load per-conversation stats from HTML state."""
        # Create mock HTML state with per-conversation stats
        html_state = {
            'stats': {'num_sms': 390, 'num_calls': 25, ...},
            'conversations': {
                'Alice': {
                    'sms_count': 234,
                    'call_count': 12,
                    'voicemail_count': 3,
                    'attachment_count': 45
                },
                'Bob': {'sms_count': 156, ...}
            }
        }

        # Write mock state
        state_file = context.output_dir / "html_processing_state.json"
        state_file.write_text(json.dumps(html_state))

        # Execute stage
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="<html>{conversation_rows}</html>"):
                with patch('pathlib.Path.write_text'):
                    result = stage.execute(context)

        # Verify metadata has correct stats
        # (would need to inspect generated index.html or returned metadata)
        assert result.success is True
```

---

## Real-World Validation

### Test Plan

1. **Run Phase 3a with enhancement**:
   ```bash
   python cli.py html-generation
   ```
   - Verify `html_processing_state.json` has `conversations` field
   - Verify 6,847 conversation entries exist
   - Verify per-conversation stats look reasonable

2. **Run Phase 4 with enhancement**:
   ```bash
   python cli.py index-generation
   ```
   - Verify index.html table rows show non-zero stats
   - Verify per-conversation stats match expectations

3. **Validation checks**:
   - Sum of per-conversation SMS counts = global SMS count (146,123)
   - Sum of per-conversation call counts = global call count (30,346)
   - Each conversation shows realistic counts (not all zeros)

---

## Backward Compatibility

### Handling Old State Files

**Issue**: Existing `html_processing_state.json` files don't have `conversations` field

**Solution**: Graceful fallback

```python
# In Phase 4's _load_html_state():
if 'conversations' not in state:
    logger.warning("No per-conversation stats found - using zeros")
    state['conversations'] = {}
```

**Result**: Old state files work but show zeros (expected), new state files show real stats

### Migration Path

**For users with existing data**:
1. Re-run Phase 3a to regenerate HTML and state file with per-conversation stats
2. Re-run Phase 4 to regenerate index with correct stats

**No breaking changes**: Old files continue to work, just show zeros until regenerated

---

## File Size Impact

### Current State File Size
- **Current**: ~1.5 MB (61,484 file paths + global stats)

### Enhanced State File Size
- **Per-conversation stats**: ~6,847 conversations × ~200 bytes = 1.3 MB
- **Total**: ~2.8 MB (manageable)

**Performance impact**: Negligible (JSON loading is fast)

---

## Implementation Checklist

### Phase 3a Changes
- [ ] Add `_extract_conversation_stats()` helper method
- [ ] Update `execute()` to call helper and store stats
- [ ] Add unit tests for per-conversation stat tracking
- [ ] Verify ConversationManager has necessary data

### Phase 4 Changes
- [ ] Replace `_load_html_stats()` with `_load_html_state()`
- [ ] Update `_build_conversation_metadata()` signature
- [ ] Merge conversation stats with file metadata
- [ ] Update unit tests to verify stat loading

### Testing
- [ ] Write 2-3 new unit tests for Phase 3a
- [ ] Update 2-3 existing unit tests for Phase 4
- [ ] All tests passing
- [ ] Real-world validation with 6,847 conversations

### Documentation
- [ ] Update `PHASE3_COMPLETE.md` with enhancement notes
- [ ] Update `PHASE4_COMPLETE.md` with enhancement notes
- [ ] Document new state file format

---

## Estimated Timeline

| Task | Time | Notes |
|------|------|-------|
| **Phase 3a enhancement** | 15-20 min | Add stat tracking |
| **Phase 4 enhancement** | 10-15 min | Load and display stats |
| **Unit tests** | 5-10 min | 4-5 new/updated tests |
| **Real-world validation** | 5 min | Test with 6,847 files |
| **Total** | **30-45 min** | End-to-end |

---

## Potential Risks

### Risk 1: ConversationManager Doesn't Track Stats

**Risk**: ConversationManager may not have per-conversation counts readily available

**Investigation needed**: Check `core/conversation_manager.py` for existing stat tracking

**Mitigation**: If not available, may need to add tracking first (adds 10-15 min)

### Risk 2: Large State File Performance

**Risk**: 2.8 MB state file may slow down JSON loading

**Mitigation**: JSON loading is fast (<100ms), not a real concern for this size

### Risk 3: Memory Usage During HTML Generation

**Risk**: Storing stats for 6,847 conversations in memory

**Mitigation**: Each conversation is ~200 bytes, total ~1.3 MB - negligible

---

## Success Criteria

### Implementation Complete When:

- [x] Phase 3a stores per-conversation stats in state file
- [x] Phase 4 loads per-conversation stats from state file
- [x] All unit tests passing (existing + new)
- [x] Real-world test: index.html shows correct per-conversation stats
- [x] Validation: Per-conversation stats sum to global stats
- [x] No breaking changes to existing commands

### Real-World Validation:

- [ ] Generate HTML with Phase 3a (with enhancement)
- [ ] Verify `html_processing_state.json` has 6,847 conversation entries
- [ ] Generate index with Phase 4 (with enhancement)
- [ ] Verify index.html table rows show non-zero stats
- [ ] Spot-check 5-10 conversations for accuracy

---

## Next Steps

**After plan approval**:

1. Investigate ConversationManager stat tracking (5 min)
2. Implement Phase 3a enhancement (15-20 min)
3. Implement Phase 4 enhancement (10-15 min)
4. Write/update unit tests (5-10 min)
5. Real-world validation (5 min)
6. Commit and document (5 min)

**Total estimated time**: 30-45 minutes

---

**Ready to proceed with implementation?**
