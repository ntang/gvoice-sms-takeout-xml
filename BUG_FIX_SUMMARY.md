# Bug Fix Summary: Missing SMS Messages

## Issue
SMS messages from certain files were not appearing in conversation output. Specifically, messages from `Ed Harbur - Text - 2024-12-05T23_40_41Z.html` (December 5th messages) were missing from `conversations/Ed_Harbur.html`.

## Root Cause
The `get_first_phone_number()` function was returning the **user's own phone number** instead of the recipient's number for files containing only outgoing messages.

### Why This Happened
1. Google Voice exports create separate HTML files for different message batches
2. Some files contain only outgoing messages (all from user to recipient)
3. `get_first_phone_number()` returned the FIRST phone number found
4. For outgoing-only files, this was always the user's number
5. Messages were then incorrectly written to the user's own conversation

### Example File Structure
```html
<!-- Ed Harbur - Text - 2024-12-05T23_40_41Z.html -->
<div class="message">
    <cite class="sender vcard">
        <a class="tel" href="tel:+13474106066">Me</a>  <!-- User's number -->
    </cite>
    <q>Message text...</q>
</div>
<div class="message">
    <cite class="sender vcard">
        <a class="tel" href="tel:+13474106066">Me</a>  <!-- User's number -->
    </cite>
    <q>Another message...</q>
</div>
```

## Solution Implemented

### Code Changes

#### 1. Modified `get_first_phone_number()` (sms.py:5666)
- Added `own_number` parameter
- Normalize `own_number` to E164 format for comparison
- Skip phone numbers matching `own_number` in all extraction strategies
- Only return `own_number` as last resort if no other number found

#### 2. Modified `get_first_phone_number_cached()` (sms.py:5609)
- Added `own_number` parameter
- Pass `own_number` to underlying function

#### 3. Modified `search_fallback_numbers()` (sms.py:4326)
- Added `own_number` parameter
- Normalize and skip `own_number` when searching similar files

#### 4. Updated Call Sites
- `write_sms_messages()` now passes `own_number` when calling extraction functions

### Test Coverage
Created comprehensive test suite (`tests/unit/test_phone_extraction.py`):
- ✅ Extract from mixed incoming/outgoing messages
- ✅ Extract from outgoing-only messages (bug scenario)
- ✅ Fallback number usage
- ✅ Skip own_number in all strategies
- ✅ Backward compatibility
- ✅ Real-world Ed Harbur scenario

All 9 tests passing.

## Impact

### Before Fix
- Outgoing-only files: Messages written to user's conversation (incorrect)
- December 5th messages: Missing from Ed_Harbur.html

### After Fix
- Outgoing-only files: Messages correctly written to recipient's conversation
- December 5th messages: Will appear in Ed_Harbur.html after reprocessing

## Next Steps

### To See the Fix in Action

**Important:** Use the proper CLI interface with pipeline stages (not `sms.py` directly).

#### Method 1: Full Pipeline (Recommended)
```bash
# Step 1: Activate virtual environment
cd /Users/nicholastang/gvoice-sms-takeout-xml
source env/bin/activate

# Step 2: Clear existing state for clean regeneration
python cli.py clear-cache --all    # Now properly clears all state files!

# Step 3: Run pipeline stages in order
python cli.py attachment-mapping
python cli.py attachment-copying
python cli.py html-generation      # <- Bug fix applies here!
python cli.py index-generation
```

#### Method 2: Traditional Convert (Simpler)
```bash
# Activate virtual environment
cd /Users/nicholastang/gvoice-sms-takeout-xml
source env/bin/activate

# Clear caches and run full conversion
python cli.py clear-cache --all
python cli.py --full-run convert
```

**Note:** The bug fix takes effect during the `html-generation` stage, where conversation HTML files are created.

### Verification
Open `../gvoice-convert/conversations/Ed_Harbur.html` and verify:
- December 5th, 6:40 PM: "Apologies for taking so long to get back to you..."
- December 5th, 6:45 PM: "And just to confirm, what we discussed..."

Both messages should now appear in chronological order between December 4th and December 6th entries.

## Technical Details

### Phone Number Normalization
- All phone numbers normalized to E164 format (`+12034173178`)
- Ensures reliable comparison regardless of input format
- Handles variations: `+1 203-417-3178`, `+12034173178`, etc.

### Backward Compatibility
- `own_number` parameter is optional (defaults to `None`)
- Existing code without `own_number` continues to work
- No breaking changes to public API

## Files Modified
- `sms.py` (3 functions updated, 1 new parameter added to each)
- `tests/unit/test_phone_extraction.py` (new test file, 9 tests)
- `cli.py` (fixed clear-cache command to clear all state files)

## Commits
```
commit c51fd60 - Fix: Skip user's own number when extracting participant phone numbers
commit f2d7d80 - docs: Add bug fix summary for missing SMS messages issue
commit e36ce87 - docs: Update BUG_FIX_SUMMARY with correct CLI pipeline workflow
commit 9554214 - Fix: clear-cache --all now clears html_processing_state.json
```

## Bonus Fix: clear-cache Command

While implementing the phone number fix, we discovered that `python cli.py clear-cache --all` was not clearing `html_processing_state.json`, which prevented HTML files from being regenerated even after clearing caches.

**Fixed in commit 9554214:**
- `clear-cache --all` now properly clears html_processing_state.json
- Updated help text to document all three cache types
- Users can now truly get a clean slate for regeneration

