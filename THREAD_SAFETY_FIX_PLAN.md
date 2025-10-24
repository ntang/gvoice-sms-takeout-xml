# Thread-Safety Fix Plan

**Date**: 2025-10-21
**Estimated Effort**: 6-8 hours (4 bugs + testing)
**Approach**: TDD with comprehensive threading stress tests
**Risk Level**: Medium (changes core concurrency behavior)

---

## Table of Contents

1. [Overview](#overview)
2. [Fix Strategy](#fix-strategy)
3. [Detailed Implementation Plans](#detailed-implementation-plans)
4. [Testing Strategy](#testing-strategy)
5. [Rollout Plan](#rollout-plan)
6. [Validation Criteria](#validation-criteria)

---

## Overview

### Goals

1. **Eliminate all race conditions** in shared data structure access
2. **Maintain performance** - no significant slowdown from locking
3. **Preserve API compatibility** - no breaking changes
4. **Add comprehensive tests** - prevent regression

### Non-Goals

- **Not** rewriting parallel processing architecture
- **Not** changing external APIs
- **Not** optimizing beyond thread-safety fixes

### Success Criteria

✅ All 4 identified thread-safety issues fixed
✅ No new RuntimeError exceptions during stress tests
✅ No data corruption in 1000-iteration stress test
✅ All existing unit tests still pass
✅ Performance regression < 5%

---

## Fix Strategy

### Approach: Minimal Invasive Changes

**Principle**: Add locking with minimal code changes to reduce risk.

**Pattern**:
1. Identify shared mutable state
2. Add appropriate locks (Lock vs RLock)
3. Use context managers (`with lock:`)
4. Make atomic operations where possible

### Lock Types

**Lock**: Fast, non-reentrant
- Use for simple mutual exclusion
- Can't be acquired twice by same thread

**RLock**: Reentrant, slightly slower
- Use when same thread may acquire lock multiple times
- Safe for nested/recursive calls

**Our Choice**:
- **RLock for all fixes** (safer, performance difference negligible)

---

## Detailed Implementation Plans

### Fix #1: PhoneLookupManager Dictionary Protection

**Priority**: P0 (Critical)
**Estimated Time**: 2 hours (including tests)
**Files**: `core/phone_lookup.py`

#### Changes Required

**Step 1: Add dedicated dictionary lock**

```python
# core/phone_lookup.py, line 36-44

class PhoneLookupManager:
    def __init__(self, lookup_file: Path, enable_prompts: bool = True, skip_filtered_contacts: bool = True):
        # ... existing validation ...

        self.lookup_file = lookup_file
        self.enable_prompts = enable_prompts
        self.skip_filtered_contacts = skip_filtered_contacts
        self.phone_aliases = {}
        self.contact_filters = {}

        # Thread safety: Separate locks for different concerns
        self._file_lock = threading.RLock()  # For file I/O operations
        self._dict_lock = threading.RLock()  # NEW: For dictionary access

        self.load_aliases()
        # ... rest of init ...
```

**Step 2: Protect get_alias() method**

```python
# core/phone_lookup.py, line 310-340

def get_alias(self, phone_number: str, soup: Optional[BeautifulSoup] = None) -> str:
    """Get alias for a phone number, prompting user if not found and prompts are enabled."""
    logger.debug(f"Looking up alias for phone number: '{phone_number}'")

    # THREAD-SAFE: Acquire dict lock for all dictionary operations
    with self._dict_lock:
        if phone_number in self.phone_aliases:
            logger.debug(f"Found existing alias for {phone_number}: {self.phone_aliases[phone_number]}")
            return self.phone_aliases[phone_number]

        if not self.enable_prompts:
            # Try to automatically extract alias from HTML if provided
            if soup:
                extracted_alias = self.extract_alias_from_html(soup, phone_number)
                if extracted_alias:
                    # Store the automatically extracted alias
                    self.phone_aliases[phone_number] = extracted_alias
                    # NOTE: save_aliases_batched() will acquire _file_lock separately
                    self.save_aliases_batched()
                    logger.info(f"Automatically extracted alias '{extracted_alias}' for {phone_number}")
                    return extracted_alias

            # No alias found and prompts disabled - return phone number as-is
            return phone_number

        # ... rest of method (prompt logic) ...
        # Keep lock held for entire operation to ensure atomicity
```

**Step 3: Protect add_alias() method**

```python
# core/phone_lookup.py, line 397-406

def add_alias(self, phone_number: str, alias: str):
    """Manually add a phone number to alias mapping."""
    sanitized_alias = self.sanitize_alias(alias)

    # THREAD-SAFE: Acquire dict lock
    with self._dict_lock:
        self.phone_aliases[phone_number] = sanitized_alias

    # File save uses separate _file_lock (already thread-safe)
    self.save_aliases()
    logger.info(f"Immediately saved alias '{sanitized_alias}' for phone number {phone_number} to {self.lookup_file}")
```

**Step 4: Protect all other dictionary access methods**

Methods to protect:
- `is_filtered()` (line 408) - Read operation
- `get_filter_info()` (line 414) - Read operation
- `get_all_aliases()` (line 394) - Read operation (already uses `.copy()` which is good!)
- `exclude_number()` (line 452) - Write operation
- `unexclude_number()` (line 463) - Write operation

```python
def is_filtered(self, phone_number: str) -> bool:
    """Check if a phone number is filtered out."""
    if not self.skip_filtered_contacts:
        return False
    with self._dict_lock:
        return phone_number in self.contact_filters

def get_filter_info(self, phone_number: str) -> Optional[str]:
    """Get the filter information for a phone number, if any."""
    with self._dict_lock:
        return self.contact_filters.get(phone_number)

def get_all_aliases(self) -> Dict[str, str]:
    """Return a copy of all phone number to alias mappings."""
    with self._dict_lock:
        return self.phone_aliases.copy()

# ... similar for exclude_number(), unexclude_number() ...
```

#### Testing for Fix #1

**Test File**: `tests/unit/test_thread_safety_phone_lookup.py`

```python
"""Thread-safety tests for PhoneLookupManager."""

import threading
import pytest
from pathlib import Path
from core.phone_lookup import PhoneLookupManager


class TestPhoneLookupThreadSafety:
    """Test thread-safety of PhoneLookupManager."""

    def test_concurrent_get_alias(self, tmp_path):
        """Test that concurrent get_alias calls don't corrupt data."""
        lookup_file = tmp_path / "test_lookup.txt"
        manager = PhoneLookupManager(lookup_file, enable_prompts=False)

        # Pre-populate with some aliases
        for i in range(100):
            manager.add_alias(f"+1555{i:04d}", f"Person{i}")

        errors = []
        def worker():
            try:
                for i in range(1000):
                    phone = f"+1555{i % 100:04d}"
                    alias = manager.get_alias(phone)
                    # Verify alias is correct
                    expected = f"Person{i % 100}"
                    if alias != expected:
                        errors.append(f"Expected {expected}, got {alias}")
            except Exception as e:
                errors.append(str(e))

        # Run 16 threads concurrently
        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0, f"Errors: {errors}"

    def test_concurrent_add_alias(self, tmp_path):
        """Test that concurrent add_alias calls don't lose data."""
        lookup_file = tmp_path / "test_lookup.txt"
        manager = PhoneLookupManager(lookup_file, enable_prompts=False)

        def worker(start, count):
            for i in range(start, start + count):
                manager.add_alias(f"+1555{i:04d}", f"Person{i}")

        # Each thread adds 100 unique aliases
        threads = [
            threading.Thread(target=worker, args=(i * 100, 100))
            for i in range(16)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all 1600 aliases were added
        all_aliases = manager.get_all_aliases()
        assert len(all_aliases) == 1600, f"Expected 1600, got {len(all_aliases)}"

    def test_concurrent_read_write(self, tmp_path):
        """Test concurrent reads and writes don't corrupt data."""
        lookup_file = tmp_path / "test_lookup.txt"
        manager = PhoneLookupManager(lookup_file, enable_prompts=False)

        # Pre-populate
        for i in range(100):
            manager.add_alias(f"+1555{i:04d}", f"Person{i}")

        stop_flag = threading.Event()
        errors = []

        def reader():
            """Continuously read aliases."""
            while not stop_flag.is_set():
                try:
                    for i in range(100):
                        manager.get_alias(f"+1555{i:04d}")
                except Exception as e:
                    errors.append(f"Reader error: {e}")

        def writer():
            """Continuously update aliases."""
            counter = 100
            while not stop_flag.is_set():
                try:
                    manager.add_alias(f"+1555{counter:04d}", f"NewPerson{counter}")
                    counter += 1
                except Exception as e:
                    errors.append(f"Writer error: {e}")

        # Start readers and writers
        reader_threads = [threading.Thread(target=reader) for _ in range(8)]
        writer_threads = [threading.Thread(target=writer) for _ in range(8)]

        for t in reader_threads + writer_threads:
            t.start()

        # Run for 2 seconds
        import time
        time.sleep(2)
        stop_flag.set()

        for t in reader_threads + writer_threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0, f"Errors: {errors}"
```

**Expected Results**:
- Before fix: Intermittent failures, data corruption, occasional RuntimeError
- After fix: All tests pass consistently

---

### Fix #2: ConversationManager get_total_stats() Protection

**Priority**: P0 (Critical)
**Estimated Time**: 1 hour (simpler fix)
**Files**: `core/conversation_manager.py`

#### Changes Required

**Step 1: Add lock to get_total_stats()**

```python
# core/conversation_manager.py, line 1116-1193

def get_total_stats(self) -> Dict[str, int]:
    """Get total statistics across all conversations."""
    # THREAD-SAFE: Acquire lock before accessing shared dictionaries
    with self._lock:
        total_stats = {
            "num_sms": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "num_img": 0,
            "num_vcf": 0,
            "real_attachments": 0,
        }

        # Aggregate from conversation_stats
        for conversation_id, stats in self.conversation_stats.items():
            total_stats["num_sms"] += stats.get('sms_count', 0)
            total_stats["num_calls"] += stats.get('calls_count', 0)
            total_stats["num_voicemails"] += stats.get('voicemails_count', 0)
            total_stats["real_attachments"] += stats.get('attachments_count', 0)

        # Fallback: Count from actual message counts if statistics are missing
        total_messages = 0
        for conversation_id, file_info in self.conversation_files.items():
            if "messages" in file_info:
                total_messages += len(file_info["messages"])

        # If we have message counts but no SMS stats, use fallback
        if total_messages > 0 and total_stats["num_sms"] == 0:
            logger.warning(f"Statistics tracking failed - using fallback count: {total_messages} messages")
            total_stats["num_sms"] = total_messages

        return total_stats
```

**That's it!** Simple one-line fix (add `with self._lock:`)

#### Testing for Fix #2

**Test File**: `tests/unit/test_thread_safety_conversation_manager.py`

```python
"""Thread-safety tests for ConversationManager."""

import threading
import pytest
from pathlib import Path
from core.conversation_manager import ConversationManager


class TestConversationManagerThreadSafety:
    """Test thread-safety of ConversationManager."""

    def test_concurrent_get_total_stats(self, tmp_path):
        """Test that get_total_stats() doesn't fail during concurrent writes."""
        manager = ConversationManager(
            output_dir=tmp_path,
            buffer_size=8192,
            output_format="html"
        )

        stop_flag = threading.Event()
        errors = []

        def writer():
            """Continuously add messages."""
            counter = 0
            while not stop_flag.is_set():
                try:
                    manager.write_message_with_content(
                        conversation_id=f"Person{counter % 100}",
                        timestamp=1000000 + counter,
                        sender="Person",
                        message=f"Message {counter}",
                        message_type="sms"
                    )
                    counter += 1
                except Exception as e:
                    errors.append(f"Writer error: {e}")

        def stats_reader():
            """Continuously read stats."""
            while not stop_flag.is_set():
                try:
                    stats = manager.get_total_stats()
                    # Stats should be internally consistent
                    assert isinstance(stats, dict)
                    assert all(isinstance(v, int) for v in stats.values())
                except Exception as e:
                    errors.append(f"Stats reader error: {e}")

        # Start writers and stats readers
        writer_threads = [threading.Thread(target=writer) for _ in range(8)]
        reader_threads = [threading.Thread(target=stats_reader) for _ in range(8)]

        for t in writer_threads + reader_threads:
            t.start()

        # Run for 2 seconds
        import time
        time.sleep(2)
        stop_flag.set()

        for t in writer_threads + reader_threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0, f"Errors: {errors}"

    def test_no_dictionary_changed_error(self, tmp_path):
        """Verify we don't get 'dictionary changed size during iteration' error."""
        manager = ConversationManager(
            output_dir=tmp_path,
            buffer_size=8192,
            output_format="html"
        )

        runtime_errors = []

        def add_conversations():
            """Add conversations rapidly."""
            for i in range(1000):
                manager.write_message_with_content(
                    conversation_id=f"Person{i}",
                    timestamp=1000000 + i,
                    sender=f"Person{i}",
                    message=f"Message {i}",
                    message_type="sms"
                )

        def read_stats():
            """Read stats rapidly."""
            for _ in range(1000):
                try:
                    manager.get_total_stats()
                except RuntimeError as e:
                    if "dictionary changed size" in str(e):
                        runtime_errors.append(str(e))

        # Run both operations concurrently
        threads = [
            threading.Thread(target=add_conversations),
            threading.Thread(target=read_stats)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should be no RuntimeError
        assert len(runtime_errors) == 0, f"RuntimeErrors: {runtime_errors}"
```

**Expected Results**:
- Before fix: RuntimeError "dictionary changed size during iteration" (intermittent)
- After fix: No RuntimeError, consistent stats

---

### Fix #3: ConversationManager Content Type Tracking Atomicity

**Priority**: P1 (High)
**Estimated Time**: 30 minutes
**Files**: `core/conversation_manager.py`

#### Changes Required

**Step 1: Use dict.setdefault() for atomic initialization**

```python
# core/conversation_manager.py, line 1195-1235

def _track_conversation_content_type(self, conversation_id: str, message_type: str, message: str, attachments: list = None):
    """Track what types of content exist in each conversation for call-only filtering."""
    logger.debug(f"🔍 CALL-ONLY DEBUG: Tracking content for {conversation_id}, type={message_type}")

    # THREAD-SAFE: Use setdefault for atomic initialization
    # This is safe even without explicit lock because it's atomic at Python level
    # and we're already inside write_message_with_content() which has lock
    content = self.conversation_content_types.setdefault(conversation_id, {
        "has_sms": False,
        "has_mms": False,
        "has_voicemail_with_text": False,
        "has_calls_only": True,
        "total_messages": 0,
        "call_count": 0
    })

    # Update content tracking (safe because we have lock from parent method)
    content["total_messages"] += 1

    if message_type == "sms":
        content["has_sms"] = True
        content["has_calls_only"] = False
        logger.debug(f"🔍 CALL-ONLY DEBUG: {conversation_id} marked as SMS")
    elif message_type == "mms" or (attachments and len(attachments) > 0):
        content["has_mms"] = True
        content["has_calls_only"] = False
        logger.debug(f"🔍 CALL-ONLY DEBUG: {conversation_id} marked as MMS")
    elif message_type == "voicemail":
        if message and message.strip() and message != "[Voicemail entry]":
            content["has_voicemail_with_text"] = True
            content["has_calls_only"] = False
            logger.debug(f"🔍 CALL-ONLY DEBUG: {conversation_id} marked as voicemail with text")
    elif message_type == "call":
        content["call_count"] += 1
        logger.debug(f"🔍 CALL-ONLY DEBUG: {conversation_id} call added")
```

**Why this is better**:
- `setdefault()` is atomic at Python level (single bytecode operation)
- Returns existing value if key exists, creates if not
- Eliminates check-then-act race condition

#### Testing for Fix #3

Covered by existing tests in Fix #2 (concurrent message writing tests).

---

### Fix #4: ConversationManager finalize() Dictionary Iteration Hardening

**Priority**: P1 (High - Preventive)
**Estimated Time**: 30 minutes
**Files**: `core/conversation_manager.py`

#### Changes Required

**Step 1: Use list() to create snapshot before iteration**

```python
# core/conversation_manager.py, line 361-450

def finalize_conversation_files(self, config: Optional["ProcessingConfig"] = None):
    """
    Finalize all conversation files by writing headers and closing tags.
    """
    with self._lock:
        # Remove conversations with no messages after date filtering (if needed)
        if config and (config.exclude_older_than or config.exclude_newer_than):
            empty_conversations = []

            # DEFENSIVE: Create snapshot to avoid dict iteration issues
            for conversation_id, file_info in list(self.conversation_files.items()):
                if len(file_info["messages"]) == 0:
                    empty_conversations.append(conversation_id)
                    logger.debug(f"Removing empty conversation after date filtering: {conversation_id}")

            # ... removal logic unchanged ...

        # Remove commercial conversations (post-processing filter)
        if config and config.filter_commercial_conversations:
            commercial_conversations = []

            # DEFENSIVE: Create snapshot
            for conversation_id, file_info in list(self.conversation_files.items()):
                if self._is_commercial_conversation(conversation_id, file_info, config):
                    commercial_conversations.append(conversation_id)
                    logger.debug(f"Removing commercial conversation: {conversation_id}")

            # ... removal logic unchanged ...

        # Process all remaining conversation files
        # DEFENSIVE: Create snapshot
        for conversation_id, file_info in list(self.conversation_files.items()):
            try:
                # ... processing logic unchanged ...
```

**Why this is better**:
- `list(dict.items())` creates a snapshot copy
- Safe to iterate even if dict is modified during iteration
- Minimal performance cost (one-time copy)
- **Defensive programming** - protects against future bugs

#### Testing for Fix #4

Covered by integration tests with finalization.

---

## Testing Strategy

### Phase 1: Unit Tests (2 hours)

**New Test Files**:
1. `tests/unit/test_thread_safety_phone_lookup.py` (Fix #1)
2. `tests/unit/test_thread_safety_conversation_manager.py` (Fix #2-4)

**Test Coverage**:
- Concurrent reads
- Concurrent writes
- Mixed reads and writes
- Stress tests (1000+ iterations)
- No RuntimeError exceptions
- No data corruption

### Phase 2: Integration Tests (1 hour)

**Test File**: `tests/integration/test_parallel_processing_thread_safety.py`

```python
"""Integration tests for parallel processing thread safety."""

def test_full_pipeline_thread_safety(test_data_dir):
    """Test complete pipeline with 16 workers."""
    # Process 1000+ files with 16 parallel workers
    # Verify:
    # 1. No exceptions
    # 2. All files processed
    # 3. Statistics match expected
    # 4. No missing phone number mappings
```

### Phase 3: Stress Tests (1 hour)

**Test File**: `tests/stress/test_thread_safety_stress.py`

```python
"""Stress tests for thread safety - run for extended periods."""

@pytest.mark.slow
def test_sustained_parallel_load():
    """Run parallel processing for 5 minutes."""
    # Continuous load test
    # Monitor for:
    # - Memory leaks
    # - Deadlocks
    # - Exceptions
    # - Data corruption
```

### Phase 4: Real-World Validation (30 minutes)

**Test**: Run on actual dataset (60,000+ files)

```bash
# Before fix: May see errors, corruption
python cli.py --full-run html-generation

# After fix: Clean run, no errors
python cli.py --full-run html-generation
```

**Validation**:
- No RuntimeError exceptions in logs
- Phone number mappings complete and correct
- Statistics match expected values
- All conversations processed correctly

---

## Rollout Plan

### Phase 1: Development (6 hours)

1. ✅ Create bug report (done)
2. ✅ Create fix plan (done)
3. ⏳ Implement Fix #1 (PhoneLookupManager) - 2 hours
4. ⏳ Implement Fix #2 (get_total_stats) - 1 hour
5. ⏳ Implement Fix #3 (content type tracking) - 30 min
6. ⏳ Implement Fix #4 (finalize hardening) - 30 min
7. ⏳ Write comprehensive tests - 2 hours

### Phase 2: Testing (2 hours)

1. ⏳ Run unit tests - 15 min
2. ⏳ Run integration tests - 15 min
3. ⏳ Run stress tests - 1 hour
4. ⏳ Real-world validation - 30 min

### Phase 3: Documentation (30 minutes)

1. ⏳ Update CHANGELOG.md
2. ⏳ Update BUG_FIXES_SUMMARY.md
3. ⏳ Add threading documentation to docstrings
4. ⏳ Create THREAD_SAFETY.md guide

### Phase 4: Deployment

1. ⏳ Commit fixes with detailed messages
2. ⏳ Tag release (v2.1.0 or similar)
3. ⏳ Monitor for issues

**Total Estimated Time**: 8-9 hours

---

## Validation Criteria

### Must Pass (Blocking)

- [ ] All 443 existing unit tests pass
- [ ] All new thread-safety tests pass (40+ new tests)
- [ ] No RuntimeError during 1000-iteration stress test
- [ ] No data corruption in concurrent access tests
- [ ] Real-world run (60K files) completes without errors

### Should Pass (Non-Blocking)

- [ ] Performance regression < 5%
- [ ] Memory usage unchanged
- [ ] All stress tests pass for 5+ minutes
- [ ] Code review approval

### Nice to Have

- [ ] Performance improvement (better CPU utilization)
- [ ] Documentation updated
- [ ] Thread-safety guide created

---

## Risks and Mitigation

### Risk #1: Performance Regression

**Concern**: Adding locks might slow down processing

**Mitigation**:
- Use RLock (minimal overhead)
- Locks are only held briefly
- Benchmark before/after
- If >5% regression, optimize lock granularity

### Risk #2: Deadlock

**Concern**: Nested locks might cause deadlock

**Mitigation**:
- Use RLock (reentrant, can't deadlock with itself)
- Document lock ordering
- Stress test for 5+ minutes
- Add deadlock detection timeout in tests

### Risk #3: Breaking Changes

**Concern**: Fixes might change behavior

**Mitigation**:
- All existing tests must pass
- API unchanged
- Only internal locking added
- Real-world validation

### Risk #4: Incomplete Fix

**Concern**: Might miss some race conditions

**Mitigation**:
- Comprehensive code review
- Extensive stress testing
- Monitor production for issues
- Quick rollback plan

---

## Alternative Approaches Considered

### Alternative #1: Reader-Writer Locks

**Idea**: Use `threading.RWLock` to allow concurrent reads

**Pros**: Better performance for read-heavy workloads

**Cons**:
- Not in Python stdlib (need external library)
- More complex
- Harder to reason about

**Decision**: **Not chosen** - RLock is sufficient, simpler

### Alternative #2: Lockless Data Structures

**Idea**: Use `queue.Queue` or lock-free structures

**Pros**: Best performance

**Cons**:
- Major refactoring required
- Higher risk
- More complex

**Decision**: **Not chosen** - Too risky for this fix

### Alternative #3: Single-Threaded Processing

**Idea**: Remove parallel processing

**Pros**: No thread-safety issues!

**Cons**:
- Unacceptable performance loss (10x slower)
- User experience degradation

**Decision**: **Not chosen** - Performance is critical

---

## Post-Fix Monitoring

### Metrics to Track

1. **Error Rate**: RuntimeError exceptions (should be 0)
2. **Data Integrity**: Phone mapping completeness (should be 100%)
3. **Performance**: Processing time (should be ±5% of baseline)
4. **Memory**: No leaks (should be stable)

### Logging

Add these debug logs (only in DEBUG mode):
```python
logger.debug(f"LOCK ACQUIRED: {self.__class__.__name__}._lock by {threading.current_thread().name}")
logger.debug(f"LOCK RELEASED: {self.__class__.__name__}._lock by {threading.current_thread().name}")
```

### Alerts

Set up monitoring for:
- RuntimeError in logs → alert immediately
- Missing phone mappings → alert if >1%
- Processing time > baseline + 10% → investigate

---

## Success Metrics

### Quantitative

- ✅ 0 RuntimeError exceptions in 10,000 file run
- ✅ 100% phone number mapping coverage
- ✅ Performance within 5% of baseline
- ✅ 0 data corruption in stress tests
- ✅ All 483+ tests passing (443 existing + 40 new)

### Qualitative

- ✅ Code is more maintainable
- ✅ Thread-safety is documented
- ✅ Future bugs prevented
- ✅ Developer confidence increased

---

## Next Steps

1. **Review this plan** - Get approval before implementation
2. **Set up branch** - `fix/thread-safety-issues`
3. **Implement fixes** - Follow TDD approach
4. **Run tests** - Comprehensive validation
5. **Deploy** - Merge to main after validation

**Estimated Start Date**: TBD
**Estimated Completion**: TBD + 2 days

---

## References

- `THREAD_SAFETY_ISSUES.md` - Detailed bug report
- Bug #13 - Thread-safe logging (related fix)
- Python threading docs: https://docs.python.org/3/library/threading.html
- PEP 703 - Making the GIL optional (future consideration)

---

**Ready to proceed?** Review this plan and approve to begin implementation.
