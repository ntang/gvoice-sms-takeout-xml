# Cache Management Guide

This document explains the two caching systems used by the Google Voice SMS Takeout converter and how to manage them.

---

## Overview: Two Caches

The converter uses **two independent caches** for different purposes:

| Cache | Location | Purpose | Managed By |
|-------|----------|---------|------------|
| **Attachment Cache** | `.cache/` | Performance - Skip expensive directory scanning | `core/performance_optimizations.py` |
| **Pipeline State** | `conversations/pipeline_state/` | Workflow - Track which stages completed | `core/pipeline/state.py` |

---

## Cache 1: Attachment Cache

### What It Does
Stores the mapping of HTML `src` attributes to attachment filenames to avoid re-scanning 60,000+ files on every run.

### Location
```
/path/to/your/export/.cache/
  ├── attachment_cache.json    # Cached attachment mappings
  └── ...                       # Other performance caches
```

### Invalidation (Automatic)
The cache automatically invalidates when:
- Directory modification time changes
- File count changes by >10%
- Directory structure hash changes

### When to Clear Manually
Clear this cache if:
- You added/removed many attachment files
- You moved files between directories
- Mapping seems outdated

```bash
python cli.py clear-cache --attachment
```

---

## Cache 2: Pipeline State

### What It Does
Tracks which pipeline stages have completed successfully so they can be skipped on subsequent runs (idempotency).

### Location
```
/path/to/your/export/conversations/pipeline_state/
  ├── pipeline_state.db         # SQLite database of stage executions
  └── pipeline_config.json      # Pipeline configuration
```

### Stores
- Stage execution history
- Success/failure status
- Timing metadata
- Validation hashes (for smart stages like `attachment_mapping`)

### When to Clear Manually
Clear this cache if:
- You want to rerun a specific pipeline stage
- Pipeline seems "stuck" thinking a stage completed
- You're troubleshooting pipeline issues

```bash
python cli.py clear-cache --pipeline
```

---

## Smart Caching (Option A Implementation)

The `attachment_mapping` stage implements **smart caching** that validates whether cached data is still valid:

### Validation Checks
1. ✅ Did stage complete successfully? (pipeline state)
2. ✅ Does output file still exist?
3. ✅ Has directory changed? (hash comparison)
4. ✅ Has file count changed significantly? (>10% threshold)

If ANY check fails → Stage reruns

### Example Scenario

```bash
# Initial run - builds mapping
python cli.py attachment-mapping
# Creates: conversations/attachment_mapping.json
# Stores: directory_hash = "abc123"

# User adds 1000 new files
cp new_files/*.html Takeout/

# Second run - automatically detects change
python cli.py attachment-mapping
# Checks: directory_hash now = "def456" (different!)
# Result: Reruns mapping to include new files ✅
```

---

## Common Scenarios

### Scenario 1: Force Fresh Run

**Goal**: Rebuild everything from scratch

```bash
# Clear both caches
python cli.py clear-cache --all

# Run pipeline
python cli.py file-pipeline --max-files 80000
```

**Result**: Complete rebuild, no cached data used

---

### Scenario 2: Rerun Just One Stage

**Goal**: Rerun attachment mapping but keep other stages

```bash
# Clear only pipeline state for this stage
rm -rf conversations/pipeline_state/

# Rerun just attachment mapping
python cli.py attachment-mapping
```

**Result**: Stage reruns but uses attachment cache (fast!)

---

### Scenario 3: New Files Added

**Goal**: Process newly added files

```bash
# Just run the pipeline again - smart caching handles it!
python cli.py attachment-mapping
```

**Result**: Automatically detects new files and reruns ✅

**No manual cache clearing needed!**

---

### Scenario 4: Debugging Issues

**Goal**: Troubleshoot why stage is being skipped

```bash
# Check pipeline state
ls conversations/pipeline_state/

# Check attachment cache
ls .cache/

# Clear both to start fresh
python cli.py clear-cache --all
```

---

## CLI Commands

### Clear Attachment Cache
```bash
python cli.py clear-cache --attachment
```

### Clear Pipeline State
```bash
python cli.py clear-cache --pipeline
```

### Clear Both
```bash
python cli.py clear-cache --all
```

### View Help
```bash
python cli.py clear-cache --help
```

---

## Cache Interaction Matrix

| Action | Attachment Cache | Pipeline State | Result |
|--------|------------------|----------------|--------|
| Add files | Auto-invalidates | Detects change | ✅ Reruns |
| Run twice | Uses cache | Skips stage | ✅ Fast |
| Clear attachment only | Rebuilt | Still thinks complete | ⚠️ Reruns slowly |
| Clear pipeline only | Uses cache | Thinks incomplete | ✅ Reruns fast |
| Clear both | Rebuilt | Thinks incomplete | ✅ Full rebuild |

---

## Best Practices

### ✅ DO

- Let smart caching handle file changes automatically
- Use `clear-cache --all` when truly starting fresh
- Check both cache locations when debugging

### ❌ DON'T

- Manually edit cache files (SQLite or JSON)
- Delete only part of a cache directory
- Assume cache is the problem without checking

---

## Troubleshooting

### Problem: Stage won't rerun even after adding files

**Check**: Is the directory hash actually changing?

```bash
# Look at current hash
cat conversations/attachment_mapping.json | grep directory_hash
```

**Solution**: Clear pipeline state
```bash
python cli.py clear-cache --pipeline
```

---

### Problem: Mapping is slow every time

**Check**: Is attachment cache being invalidated unnecessarily?

```bash
# Check if cache exists
ls .cache/

# Check cache age
ls -l .cache/attachment_cache.json
```

**Solution**: Directory might be changing frequently (modification times)

---

### Problem: "Already completed" but output file missing

**Check**: Pipeline state thinks complete but output deleted

```bash
# Verify output exists
ls conversations/attachment_mapping.json
```

**Solution**: Smart caching handles this! Stage will automatically rerun.

---

## Technical Details

### Directory Hash Algorithm
```python
hash_input = f"{dir.st_mtime}_{dir.st_size}_{file_count}"
hash = MD5(hash_input)[:16]
```

**Triggers invalidation when**:
- Directory modified (files added/removed/renamed)
- File count changes
- Subdirectory structure changes

### File Count Threshold
- Tolerance: ±10%
- Example: 1000 files → threshold is 100 files
- If count changes by >100 → invalidate

---

## Migration from Old System

If you're upgrading from a version without smart caching:

```bash
# Clear old caches
rm -rf .cache/
rm -rf conversations/pipeline_state/

# Run with new system
python cli.py attachment-mapping
```

New smart caching will take effect immediately!

---

## Summary

- **Two caches**: Attachment (performance) + Pipeline (workflow)
- **Smart validation**: Auto-detects changes, no manual clearing needed
- **Clear command**: `python cli.py clear-cache --all` for fresh start
- **Best practice**: Trust smart caching, clear only when debugging

For more details, see:
- `core/pipeline/stages/attachment_mapping.py` (implementation)
- `tests/unit/test_attachment_mapping_stage.py` (behavior specs)
- `SPIKE_FINDINGS.md` (design decisions)
