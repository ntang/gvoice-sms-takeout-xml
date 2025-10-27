#!/usr/bin/env python3
"""
Extract sender names from conversation content and propose phone_lookup.txt updates.

Scans conversation HTML files for patterns that reveal sender identities:
- "This is [Name]"
- "Hi, I'm [Name]"
- "My name is [Name]"
- Signature patterns
- Context clues
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from core.html_conversation_parser import HTMLConversationParser
from core.phone_lookup import PhoneLookupManager


def extract_name_from_introduction(text: str) -> Optional[str]:
    """
    Extract names from common introduction patterns.

    Returns:
        Extracted name or None
    """
    patterns = [
        # "This is [Name]"
        r'(?:this is|i\'?m|i am|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        # "Hi, I'm [Name]"
        r'(?:hi|hello|hey)[\s,]+(?:this is|i\'?m|i am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        # "[Name] here"
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+here',
        # "It's [Name]"
        r'(?:it\'?s|this\'?s)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        # Signatures at end: "Thanks, [Name]" or "- [Name]"
        r'(?:thanks|regards|sincerely|best)[\s,]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$',
        r'^-\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$',
    ]

    text = text.strip()
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            if name.lower() not in ['me', 'you', 'stop', 'help', 'yes', 'no', 'ok', 'okay']:
                return name

    return None


def extract_context_clues(messages: List[Dict]) -> Optional[str]:
    """
    Extract names from context clues across multiple messages.

    Looks for patterns like:
    - "Can you please send me your Venmo username" -> look in next message
    - Apartment numbers, professional titles
    """
    for i, msg in enumerate(messages):
        text = msg.get('text', '')

        # Check if message asks for contact info
        if re.search(r'(?:venmo|paypal|zelle|cashapp)\s+(?:username|name|handle)', text, re.IGNORECASE):
            # Look at next message from sender
            if i + 1 < len(messages):
                next_msg = messages[i + 1]
                if next_msg.get('sender') != 'Me':
                    next_text = next_msg.get('text', '').strip()
                    # Try to extract username/name
                    match = re.search(r'^([A-Za-z][\w-]+)[\s.,!]*$', next_text)
                    if match:
                        return match.group(1)

        # Check for apartment references
        match = re.search(r'(?:apt|apartment|unit)\s+(\d+[A-Z]?)', text, re.IGNORECASE)
        if match:
            apt = match.group(1)
            # See if name is mentioned nearby
            name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
            if name_match:
                return f"{name_match.group(1)}_apt{apt}"

    return None


def analyze_conversations(conversations_dir: Path, phone_lookup_file: Path) -> List[Tuple[str, str, str]]:
    """
    Analyze conversations and extract potential sender names.

    Returns:
        List of (phone_number, proposed_name, evidence) tuples
    """
    parser = HTMLConversationParser()

    # Load existing phone lookup
    phone_lookup = PhoneLookupManager(phone_lookup_file)
    existing_aliases = phone_lookup.get_all_aliases()

    # Find all conversation HTML files
    html_files = sorted([
        f for f in conversations_dir.glob("*.html")
        if f.name != "index.html" and not f.name.endswith(".archived.html")
    ])

    print(f"Analyzing {len(html_files)} conversation files...")
    print()

    proposals = []

    for html_file in html_files:
        try:
            conv_data = parser.parse_conversation_file(html_file)
            if not conv_data:
                continue

            phone_number = conv_data['conversation_id']
            messages = conv_data['messages']

            # Skip if already has alias
            if phone_number in existing_aliases:
                continue

            # Skip if no messages
            if not messages:
                continue

            # Try to extract name from first few messages
            extracted_name = None
            evidence = None

            for msg in messages[:10]:  # Check first 10 messages
                text = msg.get('text', '')
                if not text or msg.get('sender') == 'Me':
                    continue

                name = extract_name_from_introduction(text)
                if name:
                    extracted_name = name
                    evidence = f"Introduction: '{text[:80]}...'" if len(text) > 80 else f"Introduction: '{text}'"
                    break

            # Try context clues if no introduction found
            if not extracted_name:
                name = extract_context_clues(messages)
                if name:
                    extracted_name = name
                    evidence = "Context clues from conversation"

            if extracted_name:
                # Format name for phone_lookup.txt (lowercase, underscores)
                formatted_name = extracted_name.replace(' ', '_').replace('-', '_')
                proposals.append((phone_number, formatted_name, evidence))

        except Exception as e:
            print(f"⚠️  Error processing {html_file.name}: {e}")
            continue

    return proposals


def main():
    conversations_dir = Path("/Users/nicholastang/gvoice-convert/conversations")
    phone_lookup_file = Path("/Users/nicholastang/gvoice-convert/phone_lookup.txt")

    if not conversations_dir.exists():
        print(f"❌ Conversations directory not found: {conversations_dir}")
        return

    if not phone_lookup_file.exists():
        print(f"❌ phone_lookup.txt not found: {phone_lookup_file}")
        return

    proposals = analyze_conversations(conversations_dir, phone_lookup_file)

    if not proposals:
        print("✅ No new sender names found in conversations")
        return

    print(f"📋 Found {len(proposals)} potential new entries for phone_lookup.txt:\n")
    print("=" * 80)

    for phone, name, evidence in proposals:
        print(f"Phone: {phone}")
        print(f"Name:  {name}")
        print(f"Evidence: {evidence}")
        print(f"Proposed entry: {phone}|{name}")
        print("-" * 80)

    # Save proposals to file
    output_file = Path("phone_lookup_proposals.txt")
    with open(output_file, 'w') as f:
        f.write("# Proposed additions to phone_lookup.txt\n")
        f.write("# Review these entries before adding to phone_lookup.txt\n")
        f.write("#\n")
        f.write("# Format: phone_number|alias\n")
        f.write("# To filter, add: phone_number|alias|filter\n")
        f.write("#\n\n")

        for phone, name, evidence in proposals:
            f.write(f"# Evidence: {evidence}\n")
            f.write(f"{phone}|{name}\n\n")

    print(f"\n✅ Proposals saved to: {output_file}")
    print(f"\nReview the proposals and manually add desired entries to phone_lookup.txt")


if __name__ == "__main__":
    main()
