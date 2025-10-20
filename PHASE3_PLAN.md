# Phase 3 Plan: HTML Generation Stage

**Date**: 2025-10-20
**Status**: 📋 **PLANNING**
**Complexity**: ⚠️ **HIGH** - Most complex phase yet
**Estimated Effort**: 27-36 hours

---

## Executive Summary

Phase 3 will extract HTML processing logic from `sms.main()` into a pipeline stage with conversation-level resumability. This is the most critical and complex phase, as it handles the core business logic of the application.

**Goal**: Enable resumable HTML conversation generation without reprocessing all 62,314 files on interruption.

---

## Current State Analysis

### What `sms.main()` Currently Does

1. **Attachment Mapping** (lines 910-963)
   - Builds `src_filename_map` dictionary
   - Maps attachment references to file paths
   - **STATUS**: ✅ Already extracted to Phase 1

2. **Attachment Copying** (lines 972-982)
   - Copies attachments to output directory
   - **STATUS**: ✅ Already extracted to Phase 2

3. **HTML Processing** (lines 984-999)
   - Calls `process_html_files_param()`
   - Processes 62,314 HTML files
   - Writes messages to conversation buffers
   - **STATUS**: ❌ **NEEDS EXTRACTION** (Phase 3 target)

4. **Conversation Finalization** (lines 1001-1005)
   - Calls `conversation_manager.finalize_conversation_files()`
   - Writes buffered messages to HTML files
   - **STATUS**: ❌ **NEEDS EXTRACTION** (Phase 3 target)

5. **Index Generation** (lines 1007-1011)
   - Generates index.html
   - Lists all conversations
   - **STATUS**: Could be Phase 4 or part of Phase 3

### Key Functions Involved

| Function | Location | Complexity | Notes |
|----------|----------|------------|-------|
| `process_html_files_param()` | sms.py:2407 | Medium | Orchestrator function |
| `process_html_files()` | sms.py:2240 | Medium | Main processing loop |
| `process_html_files_batch()` | sms.py:6888 | High | Batch processing for large datasets |
| `process_single_html_file()` | file_processor.py:27 | Medium | Per-file processing |
| `process_sms_mms_file()` | sms.py | High | Message extraction |
| `conversation_manager.write_message_with_content()` | ConversationManager | Medium | Message buffering |
| `conversation_manager.finalize_conversation_files()` | ConversationManager | High | File writing |
| `conversation_manager.generate_index_html()` | ConversationManager | Medium | Index generation |

### Dependencies

**Phase 3 depends on:**
- ✅ Phase 1: attachment_mapping (provides src_filename_map)
- ✅ Phase 2: attachment_copying (copies files to output)
- ⚠️ ConversationManager (existing, needs enhancement for resumability)
- ⚠️ PhoneLookupManager (existing)
- ⚠️ FilteringService (existing)

---

## Problem Analysis

### Challenge 1: Conversation-Level Granularity

Unlike Phases 1-2 which operate on files, Phase 3 operates on **conversations**:
- 62,314 HTML files → ~thousands of conversations
- One conversation = multiple HTML files (group chats, ongoing threads)
- Messages buffered in memory until finalization
- No way to know conversation boundaries until all files processed

**Implication**: Resumability must be conversation-aware, not just file-aware.

### Challenge 2: In-Memory Buffering

`ConversationManager` buffers messages in memory:
```python
self.message_buffer = {}  # conversation_id → list of messages
```

- Messages not written to disk until `finalize_conversation_files()`
- If interrupted, all buffered messages lost
- No intermediate state tracking

**Implication**: Need persistent state to track which conversations completed.

### Challenge 3: Multi-File Conversations

A single conversation can span multiple HTML files:
- Group chat "Alice, Bob, Charlie" has 500 files
- If we resume after processing 250 files, we can't know conversation is incomplete
- Partial conversations would corrupt output

**Implication**: Must track files processed per conversation.

### Challenge 4: Filtering Complexity

Messages are filtered during processing:
- Date range filtering
- Phone number filtering
- Call-only conversation filtering

**Implication**: Can't pre-determine which files will contribute to final output.

### Challenge 5: Statistics Tracking

Stats accumulated across all files:
```python
stats = {
    "num_sms": 0,
    "num_img": 0,
    "num_vcf": 0,
    "num_calls": 0,
    "num_voicemails": 0,
}
```

**Implication**: Resumability must preserve statistics from previous runs.

---

## Proposed Solution

### Architecture: Two-Stage Approach

**Stage 3A: HTML Processing Stage** (Phase 3a)
- Processes HTML files and writes messages to conversations
- Tracks which conversations have been started/completed
- Implements conversation-level resumability

**Stage 3B: Index Generation Stage** (Phase 3b or Phase 4)
- Generates index.html after all conversations finalized
- Relatively simple, could be separate stage

### Conversation State Tracking

**New State File**: `conversation_state.json`
```json
{
  "metadata": {
    "total_conversations": 1523,
    "total_files_processed": 62314,
    "total_sms": 125000,
    "total_img": 8500,
    "total_vcf": 350,
    "total_calls": 12000,
    "total_voicemails": 450
  },
  "conversations": {
    "Alice": {
      "status": "completed",
      "files_processed": 120,
      "total_messages": 450,
      "last_updated": "2025-10-20T12:34:56Z"
    },
    "Group_Bob_Charlie_Dave": {
      "status": "in_progress",
      "files_processed": 50,
      "total_messages": 200,
      "last_updated": "2025-10-20T12:35:10Z"
    },
    "Unknown_UN_abc123": {
      "status": "pending",
      "files_processed": 0,
      "total_messages": 0,
      "last_updated": null
    }
  }
}
```

### Processing Strategy

**Option A: File-First with Conversation Tracking** (Recommended)

1. Load conversation_state.json (if exists)
2. Scan all HTML files
3. For each file:
   - Determine which conversation(s) it belongs to
   - Check if conversation already completed (skip)
   - If not completed, process file and buffer messages
4. After each conversation finalized:
   - Write conversation HTML file
   - Update conversation_state.json (mark completed)
   - Clear buffer for that conversation
5. Generate index after all conversations complete

**Pros:**
- Conversation-level resumability
- Graceful interruption recovery
- Incremental progress tracking

**Cons:**
- Need to determine conversation boundaries upfront
- More complex state management

**Option B: Two-Pass Approach**

Pass 1: Discovery
- Scan all files, build conversation → file mapping
- Save to conversation_files.json

Pass 2: Processing
- Process conversations one at a time
- Track completion in conversation_state.json

**Pros:**
- Clear separation of concerns
- Easier to reason about

**Cons:**
- Requires two full scans (slower)
- More disk I/O

**Recommendation**: Use Option A with conversation discovery during processing.

---

## Implementation Plan

### Phase 3a: HTML Processing Stage

#### Sub-Task 1: Conversation State Manager (~6 hours)

**File**: `core/conversation_state.py`

```python
class ConversationState:
    """Tracks conversation processing state for resumability."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.conversations = {}
        self.metadata = {}
        self.load()

    def is_conversation_completed(self, conversation_id: str) -> bool:
        """Check if conversation already processed."""
        return self.conversations.get(conversation_id, {}).get('status') == 'completed'

    def mark_conversation_completed(self, conversation_id: str, stats: Dict):
        """Mark conversation as completed."""
        self.conversations[conversation_id] = {
            'status': 'completed',
            'files_processed': stats['files_processed'],
            'total_messages': stats['total_messages'],
            'last_updated': datetime.now().isoformat()
        }
        self.save()

    def get_incomplete_conversations(self) -> List[str]:
        """Get list of incomplete conversation IDs."""
        return [
            conv_id for conv_id, data in self.conversations.items()
            if data.get('status') != 'completed'
        ]

    def load(self):
        """Load state from JSON."""
        # Implementation

    def save(self):
        """Save state to JSON."""
        # Implementation
```

**Tests**: 8-10 tests
- Load/save state
- Mark conversations complete
- Check completion status
- Get incomplete conversations
- Handle missing state file

#### Sub-Task 2: Enhanced ConversationManager (~8 hours)

**Modify**: `core/conversation_manager.py`

**New methods:**
```python
def finalize_single_conversation(self, conversation_id: str, config):
    """Finalize a single conversation (not all conversations)."""
    # Write buffered messages for one conversation
    # Return stats for state tracking

def get_conversation_stats(self, conversation_id: str) -> Dict:
    """Get statistics for a specific conversation."""
    return {
        'files_processed': self.conversation_files[conversation_id]['file_count'],
        'total_messages': self.conversation_files[conversation_id]['message_count'],
        # ... other stats
    }
```

**Challenges:**
- Current `finalize_conversation_files()` processes ALL conversations
- Need granular finalization
- Must preserve existing behavior for backward compatibility

#### Sub-Task 3: HTML Processing Pipeline Stage (~10 hours)

**File**: `core/pipeline/stages/html_generation.py`

```python
class HtmlGenerationStage(PipelineStage):
    """
    Pipeline stage that generates HTML conversation files.

    Processes HTML files from processing_dir and generates conversation HTML.
    Implements conversation-level resumability.
    """

    def __init__(self):
        super().__init__("html_generation")

    def get_dependencies(self) -> List[str]:
        return ["attachment_mapping", "attachment_copying"]

    def validate_prerequisites(self, context: PipelineContext) -> bool:
        # Verify attachments copied
        # Verify attachment mapping exists
        return True

    def can_skip(self, context: PipelineContext) -> bool:
        # Check conversation_state.json
        # Skip if all conversations completed
        state = ConversationState(context.output_dir / "conversation_state.json")
        return len(state.get_incomplete_conversations()) == 0

    def execute(self, context: PipelineContext) -> StageResult:
        # Load conversation state
        state = ConversationState(...)

        # Load attachment mapping
        with open(context.output_dir / "attachment_mapping.json") as f:
            mapping_data = json.load(f)
            src_filename_map = self._convert_mapping_to_dict(mapping_data)

        # Initialize conversation manager
        conversation_manager = ConversationManager(...)

        # Get HTML files
        html_files = list((context.processing_dir / "Calls").rglob("*.html"))

        # Process files
        conversations_completed = []
        for html_file in html_files:
            # Determine conversation ID for this file
            # (This requires parsing the file - expensive!)
            conversation_id = self._get_conversation_id_for_file(html_file, ...)

            # Skip if already completed
            if state.is_conversation_completed(conversation_id):
                continue

            # Process file
            process_single_html_file(html_file, ...)

            # Check if conversation ready to finalize
            # (How do we know? This is the hard part!)
            if self._is_conversation_complete(conversation_id, ...):
                # Finalize conversation
                conversation_manager.finalize_single_conversation(conversation_id)

                # Update state
                stats = conversation_manager.get_conversation_stats(conversation_id)
                state.mark_conversation_completed(conversation_id, stats)

                conversations_completed.append(conversation_id)

        # Finalize any remaining conversations
        conversation_manager.finalize_conversation_files()

        return StageResult(
            success=True,
            records_processed=len(conversations_completed),
            metadata={
                'conversations_completed': len(conversations_completed),
                'total_conversations': len(state.conversations),
                # ... stats
            }
        )
```

**Critical Challenge**: How do we know when a conversation is "complete"?

**Solution Options:**

1. **Discovery Pass**: Scan all files first, build conversation → files mapping
   - Pro: Know exactly which files belong to which conversation
   - Con: Requires full scan upfront (slow)

2. **Hash-Based**: Hash (conversation_id + all files in processing dir)
   - Pro: Can detect if new files added
   - Con: Doesn't help with partial processing

3. **Lazy Finalization**: Don't finalize until all files processed
   - Pro: Simple - same as current behavior
   - Con: No incremental progress (defeats resumability purpose!)

4. **Chunked Processing**: Process files in chunks, finalize conversations after each chunk
   - Pro: Incremental progress
   - Con: Some conversations might span multiple chunks

**Recommendation**: Use Discovery Pass (Option 1) for accuracy.

#### Sub-Task 4: File-to-Conversation Mapping (~4 hours)

**File**: `core/pipeline/stages/html_generation.py`

```python
def build_file_conversation_mapping(
    processing_dir: Path,
    phone_lookup_manager: PhoneLookupManager
) -> Dict[str, str]:
    """
    Build mapping of HTML file → conversation ID.

    This requires parsing each file to extract participants.
    Expensive but necessary for accurate resumability.

    Returns:
        Dict mapping file path → conversation ID
    """
    mapping = {}
    html_files = list((processing_dir / "Calls").rglob("*.html"))

    for html_file in html_files:
        # Parse file to get participants
        soup = parse_html_file(html_file)
        participants = extract_participants(soup, phone_lookup_manager)

        # Generate conversation ID
        conversation_id = generate_conversation_id(participants, ...)

        mapping[str(html_file)] = conversation_id

    return mapping
```

**Caching**: Save to `file_conversation_mapping.json` to avoid reparsing.

#### Sub-Task 5: Tests (~6-8 hours)

**Test Coverage** (estimate 25-30 tests):

1. **ConversationState tests** (8-10 tests)
   - Load/save state
   - Mark conversations complete
   - Get incomplete conversations
   - Handle missing/corrupt state files

2. **HtmlGenerationStage tests** (10-12 tests)
   - Basic properties (name, dependencies)
   - Prerequisite validation
   - Execution with empty state
   - Execution with partial state
   - Resumability after interruption
   - Smart skipping
   - Error handling

3. **File-Conversation Mapping tests** (5-6 tests)
   - Build mapping for various file structures
   - Handle group conversations
   - Handle individual conversations
   - Cache loading/saving

4. **Integration tests** (2-3 tests)
   - Full pipeline execution
   - Resume after interruption
   - State consistency

---

## Risks and Mitigations

### Risk 1: Performance Degradation

**Risk**: Discovery pass doubles processing time
**Mitigation**:
- Cache file-conversation mapping
- Use optimized parsing (BeautifulSoup with lxml)
- Process discovery in parallel

### Risk 2: State Corruption

**Risk**: Interruption during state save corrupts file
**Mitigation**:
- Atomic writes (write to .tmp, then rename)
- Validate JSON on load
- Keep backup of previous state

### Risk 3: Breaking Existing Functionality

**Risk**: Changes to ConversationManager break convert command
**Mitigation**:
- Maintain backward compatibility
- Keep existing methods intact
- Add new methods for pipeline use
- Comprehensive integration tests

### Risk 4: Incomplete Conversation Detection

**Risk**: False positives marking conversations complete
**Mitigation**:
- Strict validation of completion criteria
- Log all completion decisions
- Provide command to reset state if needed

### Risk 5: Memory Consumption

**Risk**: Loading all state into memory for large datasets
**Mitigation**:
- Use streaming JSON parsing for large states
- Implement state pagination
- Clear completed conversations from memory

---

## Testing Strategy

### Unit Tests (TDD)

Write tests BEFORE implementation:
1. ConversationState class (8-10 tests)
2. HtmlGenerationStage (10-12 tests)
3. File mapping builder (5-6 tests)

**Total**: ~25-30 unit tests

### Integration Tests

Test with real Google Voice export:
1. Full run (all 62k files)
2. Interrupted run (stop after 30k files, resume)
3. Multiple interruptions
4. State corruption recovery

### Performance Tests

Measure:
- Discovery pass time
- State save/load time
- Memory consumption
- Conversation finalization time

**Targets**:
- Discovery: <2min for 62k files
- State operations: <1s
- Memory: <500MB peak
- Per-conversation finalization: <100ms

---

## Estimated Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| **Sub-Task 1**: ConversationState | 6h | State management class + tests |
| **Sub-Task 2**: Enhanced ConversationManager | 8h | Add granular finalization |
| **Sub-Task 3**: HtmlGenerationStage | 10h | Main pipeline stage |
| **Sub-Task 4**: File-Conversation Mapping | 4h | Discovery pass implementation |
| **Sub-Task 5**: Comprehensive Tests | 8h | 25-30 tests |
| **Integration & Debugging** | 6h | Real-world testing |
| **Documentation** | 3h | PHASE3_COMPLETE.md, tests docs |
| **Buffer** | 6h | Unexpected issues |
| **TOTAL** | **51h** | Upper bound estimate |

**Realistic Estimate**: 27-36 hours (based on Phase 1+2 experience)

---

## Alternative Approach: Simpler Resumability

### Simplified Design (Lower Complexity)

**Idea**: Don't track individual conversations, just track files processed.

**State File**: `html_processing_state.json`
```json
{
  "files_processed": [
    "/path/to/file1.html",
    "/path/to/file2.html",
    ...
  ],
  "stats": {
    "num_sms": 1000,
    "num_img": 50,
    ...
  }
}
```

**Processing**:
1. Load state (list of processed files)
2. Filter HTML files list to exclude processed ones
3. Process remaining files normally
4. Update state after each file
5. Finalize all conversations at end (same as current)

**Pros**:
- Much simpler implementation
- Less risk of breaking existing code
- Easier to test

**Cons**:
- No incremental finalization
- If interrupted before finalization, lose all work
- Can't resume partial conversations

**Recommendation**: Start with this approach for Phase 3a, add conversation-level resumability in Phase 3b if needed.

---

## Recommended Phases

### Phase 3a: File-Level Resumability (Simpler)

**Effort**: 12-16 hours

**Scope**:
- Track which files processed
- Skip already-processed files on resume
- Finalize all conversations at end (like current)

**Benefits**:
- Easier to implement
- Lower risk
- Still provides value (can resume after interruption)

### Phase 3b: Conversation-Level Resumability (Optional)

**Effort**: 15-20 hours

**Scope**:
- Add conversation state tracking
- Implement incremental finalization
- Discovery pass for file-conversation mapping

**Benefits**:
- True incremental progress
- Can see partial results before completion
- More robust resumability

**When to do**: After Phase 3a validates successfully and if user needs it.

---

## Success Criteria

### Phase 3a (Simpler)

- [ ] All unit tests passing (15-20 tests)
- [ ] Can process all 62k files
- [ ] Can resume after interruption (file-level)
- [ ] No regression in convert command
- [ ] Performance acceptable (<10% slower than current)
- [ ] Documentation complete

### Phase 3b (Full - Optional)

- [ ] All unit tests passing (25-30 tests)
- [ ] Conversation-level resumability working
- [ ] Incremental finalization working
- [ ] State management robust
- [ ] Performance acceptable
- [ ] Documentation complete

---

## Next Steps

### Immediate Actions

1. **User Decision**: Choose between:
   - Option A: Phase 3a only (simpler, file-level resumability)
   - Option B: Full Phase 3 (complex, conversation-level resumability)

2. **Review Plan**: User provides feedback on approach

3. **TDD Implementation**: Write tests first, then implement

### Phase 3a Timeline (Recommended Start)

**Week 1** (12-16 hours):
- Day 1-2: Write tests for file state tracking (TDD red phase)
- Day 3-4: Implement HtmlGenerationStage (basic version)
- Day 5: Integration testing and debugging
- Day 6: Documentation

**Deliverables**:
- `core/pipeline/stages/html_generation.py`
- `tests/unit/test_html_generation_stage.py`
- `PHASE3A_COMPLETE.md`
- `test_phase3a.sh`

---

## Questions for User

1. **Complexity Preference**: Do you want Phase 3a (simpler, file-level) or full Phase 3 (conversation-level)?

2. **Interruption Frequency**: How often do you expect to interrupt processing?
   - If rarely: Phase 3a sufficient
   - If often: Full Phase 3 worth the effort

3. **Partial Results**: Do you need to see partial conversation results before all files processed?
   - If no: Phase 3a sufficient
   - If yes: Need full Phase 3

4. **Timeline**: Do you want to proceed with Phase 3 now, or take a break after Phases 1+2?

---

## Conclusion

Phase 3 is significantly more complex than Phases 1+2 combined. The recommended approach is to start with Phase 3a (simpler, file-level resumability) and validate it works before considering Phase 3b (conversation-level resumability).

**Estimated Effort**:
- Phase 3a: 12-16 hours
- Phase 3b: 15-20 hours (if needed)
- Total: 27-36 hours (if doing both)

**Recommendation**: Start with Phase 3a, validate with real data, then decide if Phase 3b is necessary.
