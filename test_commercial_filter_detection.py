#!/usr/bin/env python3
"""
Test script to analyze commercial conversation detection.

This script analyzes existing conversation HTML files to determine how many
would be detected as commercial/spam without actually deleting anything.

Usage:
    python test_commercial_filter_detection.py
"""

import json
from pathlib import Path
from typing import Dict, List
from core.commercial_filter import is_commercial_conversation

def extract_messages_from_state_file(state_file: Path) -> Dict[str, List[Dict]]:
    """
    Extract conversation messages from html_processing_state.json.

    Args:
        state_file: Path to html_processing_state.json

    Returns:
        Dictionary mapping conversation_id to list of messages
    """
    if not state_file.exists():
        print(f"❌ State file not found: {state_file}")
        return {}

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)

        conversations = state.get('conversations', {})
        print(f"📊 Found {len(conversations)} conversations in state file")

        # Note: The state file only has per-conversation stats, not messages
        # We'll need to analyze actual HTML files or conversation data
        return conversations

    except Exception as e:
        print(f"❌ Error reading state file: {e}")
        return {}


def analyze_conversations_directory(output_dir: Path) -> None:
    """
    Analyze conversation HTML files to detect commercial conversations.

    This is a dry-run that reports what would be detected without modifying files.

    Args:
        output_dir: Directory containing conversation HTML files and state
    """
    print("=" * 80)
    print("COMMERCIAL CONVERSATION DETECTION TEST")
    print("=" * 80)
    print()
    print(f"📂 Analyzing directory: {output_dir}")
    print()

    # Check if state file exists
    state_file = output_dir / "html_processing_state.json"

    if not state_file.exists():
        print(f"❌ State file not found: {state_file}")
        print()
        print("⚠️  This script requires html_processing_state.json to analyze conversations.")
        print("    Run 'python cli.py html-generation' first to generate the state file.")
        return

    # Load state file
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
    except Exception as e:
        print(f"❌ Error reading state file: {e}")
        return

    conversations = state.get('conversations', {})
    total_conversations = len(conversations)

    print(f"📊 Total conversations in state: {total_conversations}")
    print()

    # Note: The state file only contains statistics, not message content
    # To do a full analysis, we need message data which is only available
    # during processing (in ConversationManager's memory buffers)

    print("=" * 80)
    print("ANALYSIS APPROACH")
    print("=" * 80)
    print()
    print("⚠️  Message-level analysis requires running the pipeline with the filter.")
    print()
    print("To see what would be filtered, you have two options:")
    print()
    print("1. **Dry-run approach** (RECOMMENDED):")
    print("   - Run html-generation WITH the filter enabled")
    print("   - Check the log output for 'Commercial conversation detected' messages")
    print("   - Compare before/after conversation counts")
    print()
    print("2. **Pattern-based heuristic** (APPROXIMATE):")
    print("   - Look for conversations with very few messages (2-4 messages)")
    print("   - These are candidates but not guaranteed to be commercial")
    print()

    # Heuristic analysis: conversations with very few messages
    print("=" * 80)
    print("HEURISTIC ANALYSIS (APPROXIMATE)")
    print("=" * 80)
    print()

    very_short_convs = []
    short_convs = []

    for conv_id, stats in conversations.items():
        total_messages = (
            stats.get('sms_count', 0) +
            stats.get('call_count', 0) +
            stats.get('voicemail_count', 0)
        )

        # Commercial conversations are typically very short (2-4 messages)
        if total_messages == 2 or total_messages == 3:
            very_short_convs.append((conv_id, total_messages, stats))
        elif total_messages == 4 or total_messages == 5:
            short_convs.append((conv_id, total_messages, stats))

    print(f"🔍 Very short conversations (2-3 messages): {len(very_short_convs)}")
    print(f"   These are MOST LIKELY to be commercial (spam → STOP → confirmation)")
    print()

    if very_short_convs and len(very_short_convs) <= 20:
        print("   Examples:")
        for conv_id, msg_count, stats in very_short_convs[:10]:
            sms = stats.get('sms_count', 0)
            calls = stats.get('call_count', 0)
            print(f"   - {conv_id}: {msg_count} messages ({sms} SMS, {calls} calls)")
        print()

    print(f"🔍 Short conversations (4-5 messages): {len(short_convs)}")
    print(f"   These MIGHT include some commercial conversations")
    print()

    print("=" * 80)
    print("RECOMMENDED TESTING APPROACH")
    print("=" * 80)
    print()
    print("To get accurate counts, run the filter and compare results:")
    print()
    print("Step 1: Note current conversation count")
    print("----------------------------------------")
    print(f"  Current conversations: {total_conversations}")
    print()
    print("Step 2: Run with commercial filter enabled")
    print("-------------------------------------------")
    print("  python cli.py --filter-commercial-conversations html-generation")
    print()
    print("Step 3: Check the logs for detection messages")
    print("----------------------------------------------")
    print("  Look for lines like:")
    print("  'Commercial conversation detected: <name> (N messages)'")
    print()
    print("Step 4: Compare conversation counts")
    print("------------------------------------")
    print("  Difference = conversations that were filtered")
    print()
    print("=" * 80)
    print()


def main():
    """Main entry point for the test script."""
    # Default path - adjust if needed
    output_dir = Path("/Users/nicholastang/gvoice-convert/conversations")

    if not output_dir.exists():
        print(f"❌ Output directory not found: {output_dir}")
        print()
        print("Please update the output_dir path in this script to match your setup.")
        return

    analyze_conversations_directory(output_dir)


if __name__ == "__main__":
    main()
