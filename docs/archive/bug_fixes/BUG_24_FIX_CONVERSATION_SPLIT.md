# Bug Fix #24: Conversation Messages Split Across Multiple Files

## Issue Summary

**Reported**: User discovered that conversations were missing messages. Investigation revealed messages for the same contact were being split across TWO separate HTML files:
- One file using the phone number (e.g., `+12034173178.html`)
- One file using the alias (e.g., `Ed_Harbur.html`)

## Example Case: Ed Harbur

**Files Created**:
1. `+12034173178.html` - Contains calls and voicemails
2. `Ed_Harbur.html` - Contains text messages

**Missing Messages**: Text messages from Dec 4, 5, 7, and 9 were processed but NOT appearing in either file (they exist in source data but weren't in the output).

## Root Cause

In `sms.py`, both `write_call_entry` (line 8170) and `write_voicemail_entry` (line 8498) were calling `get_conversation_id` without passing the `phone_lookup_manager` parameter:

```python
# BEFORE (BUGGY):
conversation_id = effective_conversation_manager.get_conversation_id([phone_number], False)
```

When `phone_lookup_manager` is not passed (defaults to `None`), the `get_conversation_id` method returns the raw phone number instead of looking up the alias. This caused:
- **Text messages** to use alias-based conversation IDs (e.g., "Ed_Harbur")
- **Calls/voicemails** to use phone-number-based conversation IDs (e.g., "+12034173178")
- Messages split across two different files

## Fix Applied

**Files Modified**: `sms.py` (lines 8170 and 8498)

```python
# AFTER (FIXED):
conversation_id = effective_conversation_manager.get_conversation_id([phone_number], False, effective_phone_manager)
```

Now all message types (SMS, MMS, calls, voicemails) will use the same conversation ID generation logic, ensuring they're grouped into a single file.

## Verification

Other calls to `get_conversation_id` in the codebase were audited and confirmed to be passing `phone_lookup_manager` correctly:
- Line 3378-3380: Group conversation detection (✓ passes phone_lookup_manager)
- Line 3752-3754: Individual SMS conversation (✓ passes phone_lookup_manager)
- Line 4934-4936: Group conversation fallback (✓ passes phone_lookup_manager)

## User Action Required

To regenerate the Ed Harbur conversation with all messages combined:

1. Delete the split files:
   ```bash
   rm /Users/nicholastang/gvoice-convert/conversations/+12034173178.html
   rm /Users/nicholastang/gvoice-convert/conversations/Ed_Harbur.html
   ```

2. Clear the pipeline cache to force re-processing:
   ```bash
   python cli.py clear-cache --pipeline
   ```

3. Regenerate conversations:
   ```bash
   python cli.py html-generation
   python cli.py index-generation
   ```

This will create a single unified `Ed_Harbur.html` file with all messages (text, calls, and voicemails) in chronological order.

## Impact

**Severity**: HIGH - Messages were silently split across multiple files, making conversation histories incomplete and confusing.

**Scope**: Affects all conversations that have both:
- Phone numbers with aliases in `phone_lookup.txt`
- Mix of text messages AND calls/voicemails

## Testing Recommendations

1. Test with a contact that has both SMS and call history
2. Verify single conversation file is created
3. Verify all message types appear in chronological order
4. Check that the conversation uses the alias name (not phone number)
