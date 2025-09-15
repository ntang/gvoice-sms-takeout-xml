#!/usr/bin/env python3
"""
Debug script to test conversation manager with actual data
"""

import sys
from pathlib import Path
from core.conversation_manager import ConversationManager
from core.phone_lookup import PhoneLookupManager
from core.processing_config import ProcessingConfig

def test_conversation_with_phone_lookup():
    """Test conversation manager with phone lookup"""
    print("Testing ConversationManager with PhoneLookupManager...")
    
    # Create a test output directory
    test_dir = Path("test_conversations")
    test_dir.mkdir(exist_ok=True)
    
    # Initialize phone lookup manager
    phone_lookup = PhoneLookupManager(Path("test_phone_lookup.txt"))
    
    # Initialize conversation manager
    cm = ConversationManager(
        output_dir=test_dir,
        output_format="html"
    )
    
    # Test writing a message with a conversation ID
    conversation_id = cm.get_conversation_id(
        ["+1234567890"], 
        False, 
        phone_lookup
    )
    
    print(f"Generated conversation ID: {conversation_id}")
    
    # Test writing a message
    message_text = "Hello, this is a test message"
    timestamp = 1234567890
    
    print(f"Writing message to conversation: {conversation_id}")
    cm.write_message_with_content(
        conversation_id=conversation_id,
        message_text=message_text,
        attachments=[],
        timestamp=timestamp,
        sender="Test Sender"
    )
    
    print(f"Messages in conversation: {len(cm.conversation_files[conversation_id]['messages'])}")
    
    # Finalize the conversation
    print("Finalizing conversation files...")
    cm.finalize_conversation_files()
    
    # Check if file was created
    expected_file = test_dir / f"{conversation_id}.html"
    if expected_file.exists():
        print(f"✅ File created: {expected_file}")
        print(f"File size: {expected_file.stat().st_size} bytes")
        
        # Show first few lines
        with open(expected_file, 'r') as f:
            lines = f.readlines()[:10]
            print("First 10 lines:")
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line.rstrip()}")
    else:
        print(f"❌ File not created: {expected_file}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print("Test completed and cleaned up")

if __name__ == "__main__":
    test_conversation_with_phone_lookup()
