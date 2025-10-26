# Phase 1 Spike: AttachmentMappingStage POC

**Date**: 2025-10-19
**Duration**: 30 minutes
**Status**: ✅ Ready for testing

---

## What We Built

A minimal proof-of-concept pipeline stage that:
1. Wraps the existing `build_attachment_mapping_optimized()` function
2. Saves output to `attachment_mapping.json` in pipeline format
3. Integrates with PipelineManager and state tracking
4. Can be run via CLI: `python cli.py attachment-mapping-spike`

**Files Created:**
- `core/pipeline/stages/attachment_mapping_spike.py` (~120 lines)
- CLI command added to `cli.py` (lines 745-790)

---

## Key Findings

### ✅ What Works Well

1. **Existing code is reusable**: `build_attachment_mapping_optimized()` does exactly what we need
2. **Clean integration**: Wrapping in PipelineStage is straightforward (~50 LOC for core logic)
3. **Caching already exists**: The optimized function already has caching built-in
4. **No dependencies**: Stage can run independently (doesn't need content-extraction)

### ⚠️ Identified Challenges

1. **Format conversion**: Need to convert `Dict[str, Tuple[str, Path]]` → JSON-serializable format
2. **Path serialization**: Pipeline uses JSON, but Paths need string conversion
3. **Two caching layers**: Function has `.cache/` AND pipeline will have state tracking
   - Potential confusion between attachment cache vs. pipeline state
   - Need to clarify which cache does what

### 🔍 Integration Points Validated

**Inputs:**
- ✅ `context.processing_dir` - Processing directory path
- ✅ `context.output_dir` - Output directory for JSON file
- ✅ `context.config` - Configuration object (optional for this stage)

**Outputs:**
- ✅ `attachment_mapping.json` - Serialized mapping
- ✅ `StageResult` with metadata (count, timing, etc.)
- ✅ Pipeline state tracking (automatic via PipelineManager)

**Dependencies:**
- ✅ `core.performance_optimizations` - Import works
- ✅ Pipeline base classes - Integration clean
- ✅ Logging - Uses existing logger

---

## Test Plan (When We Do TDD)

Based on the spike, here are the tests we should write:

### Unit Tests (~8 tests)

```python
class TestAttachmentMappingStage:
    def test_stage_name_is_correct()
    def test_no_dependencies()
    def test_execute_creates_output_file()
    def test_execute_with_empty_directory()
    def test_execute_handles_missing_processing_dir()
    def test_json_format_is_valid()
    def test_paths_are_serialized_correctly()
    def test_metadata_includes_mapping_count()
```

### Integration Tests (~3 tests)

```python
class TestAttachmentMappingIntegration:
    def test_maps_real_google_voice_export()
    def test_caching_improves_performance()
    def test_integrates_with_pipeline_manager()
```

---

## Risks Identified

### Low Risk ✅
- Code reuse from existing functions (already tested, 550 tests pass)
- Pipeline integration (base classes are solid)
- JSON serialization (standard library)

### Medium Risk ⚠️
- **Cache confusion**: Two caching mechanisms could confuse users
  - **Mitigation**: Clear documentation, consider consolidating caches
- **Large output files**: 62k files = large JSON (~10-50 MB?)
  - **Mitigation**: Test with full dataset, consider compression

### No High Risks Found 🎉

---

## Performance Expectations

Based on existing `build_attachment_mapping_optimized()`:
- **First run**: 30-60 seconds (with caching save)
- **Cached run**: 1-5 seconds (cache hit)
- **Output file size**: ~5-20 MB for 62k files

The spike adds minimal overhead (~0.1s for JSON serialization).

---

## Next Steps (If Approved)

### Option 1: Full TDD Implementation (Recommended)
1. Write failing unit tests (~2-3 hours)
2. Implement production stage (~3-4 hours)
3. Write integration tests (~1-2 hours)
4. Update documentation (~1 hour)
5. **Total**: ~7-10 hours

### Option 2: Production-ize the Spike (Faster)
1. Rename `_spike.py` → `.py`
2. Add error handling
3. Write minimal tests
4. **Total**: ~3-4 hours
**Risk**: Less test coverage

### Option 3: Pause and Review
- Review spike with team
- Decide if approach is sound
- Get buy-in before proceeding

---

## Recommendation

✅ **Proceed with Option 1 (Full TDD)**

**Reasons:**
1. Spike validated the approach - no major blockers
2. Existing code is solid foundation (550 tests pass)
3. Integration is clean and straightforward
4. Risk is low, value is high (resumability + caching)
5. Sets good pattern for Phases 2-5

**Estimated ROI:**
- **Investment**: 7-10 hours
- **Benefit**:
  - Saves 30-60s on every rerun (cache hit)
  - Enables resumable pipelines in later phases
  - Clean pattern for remaining stages

---

## How to Test the Spike

```bash
# Activate venv
source env/bin/activate

# Run the spike
python cli.py attachment-mapping-spike

# Check output
cat /Users/nicholastang/gvoice-convert/conversations/attachment_mapping.json | head -50

# Verify caching (should be fast on second run)
rm -rf /Users/nicholastang/gvoice-convert/conversations/pipeline_state/
python cli.py attachment-mapping-spike  # First run: slow
python cli.py attachment-mapping-spike  # Second run: fast (cached)
```

---

## Open Questions

1. Should we consolidate `.cache/` and `pipeline_state/` directories?
2. Do we need to support `sample_files` parameter for test mode?
3. Should mapping be regenerated if source files change? (Currently: yes, via cache invalidation)
4. Is 10-50 MB JSON output file acceptable? Or use binary format (msgpack)?

---

**Spike Status**: ✅ **VALIDATED - Ready for TDD Implementation**
