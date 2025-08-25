#!/usr/bin/env python3
"""
Test script for the unified extractor.

This script tests the UnifiedExtractor class to ensure it correctly extracts
information from various types of Google Voice export files.
"""

import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from unified_extractor import UnifiedExtractor


def create_test_html(content: str) -> BeautifulSoup:
    """Create a BeautifulSoup object from HTML content for testing."""
    return BeautifulSoup(content, "html.parser")


def test_sms_extraction():
    """Test SMS extraction functionality."""
    print("🧪 Testing SMS extraction...")

    extractor = UnifiedExtractor()

    # Test SMS HTML content
    sms_html = """
    <html>
        <body>
            <div class="message">
                <abbr class="dt" title="2024-06-17T03:21:00Z">Jun 17</abbr>
                <cite><a href="tel:+15557776666">+15557776666</a></cite>
                <q>See you later!</q>
            </div>
        </body>
    </html>
    """

    soup = create_test_html(sms_html)
    result = extractor.extract_info(
        "Jane Smith - Text - 2024-06-17T03_21_00Z.html", soup, "sms"
    )

    if result:
        print(f"✅ SMS extraction successful:")
        print(f"   Phone: {result.get('phone_number')}")
        print(f"   Timestamp: {result.get('timestamp')}")
        print(f"   Content: {result.get('message_content')}")
        print(f"   Type: {result.get('type')}")
    else:
        print("❌ SMS extraction failed")

    return result is not None


def test_call_extraction():
    """Test call extraction functionality."""
    print("\n🧪 Testing call extraction...")

    extractor = UnifiedExtractor()

    # Test call HTML content
    call_html = """
    <html>
        <body>
            <div class="call-info">
                <span class="timestamp">2024-06-17T03:21:00Z</span>
                <a href="tel:+15557776666">+15557776666</a>
                <span class="duration">0:02:15</span>
            </div>
        </body>
    </html>
    """

    soup = create_test_html(call_html)
    result = extractor.extract_info(
        "Jane Smith - Placed - 2024-06-17T03_21_00Z.html", soup, "call"
    )

    if result:
        print(f"✅ Call extraction successful:")
        print(f"   Phone: {result.get('phone_number')}")
        print(f"   Timestamp: {result.get('timestamp')}")
        print(f"   Type: {result.get('type')}")
        print(f"   Duration: {result.get('duration')}")
    else:
        print("❌ Call extraction failed")

    return result is not None


def test_voicemail_extraction():
    """Test voicemail extraction functionality."""
    print("\n🧪 Testing voicemail extraction...")

    extractor = UnifiedExtractor()

    # Test voicemail HTML content
    voicemail_html = """
    <html>
        <body>
            <div class="voicemail-info">
                <span class="timestamp">2024-06-17T03:21:00Z</span>
                <a href="tel:+15557776666">+15557776666</a>
                <span class="duration">0:00:20</span>
                <div class="transcription">Hello, this is a test message.</div>
            </div>
        </body>
    </html>
    """

    soup = create_test_html(voicemail_html)
    result = extractor.extract_info(
        "Jane Smith - Voicemail - 2024-06-17T03_21_00Z.html", soup, "voicemail"
    )

    if result:
        print(f"✅ Voicemail extraction successful:")
        print(f"   Phone: {result.get('phone_number')}")
        print(f"   Timestamp: {result.get('timestamp')}")
        print(f"   Duration: {result.get('duration')}")
        print(f"   Transcription: {result.get('transcription')}")
    else:
        print("❌ Voicemail extraction failed")

    return result is not None


def test_automatic_type_detection():
    """Test automatic file type detection."""
    print("\n🧪 Testing automatic type detection...")

    extractor = UnifiedExtractor()

    test_cases = [
        ("Jane Smith - Text - 2024-06-17T03_21_00Z.html", "sms"),
        ("John Doe - MMS - 2024-06-17T03_21_00Z.html", "mms"),
        ("Bob Wilson - Placed - 2024-06-17T03_21_00Z.html", "call"),
        ("Alice Brown - Received - 2024-06-17T03_21_00Z.html", "call"),
        ("Charlie Davis - Missed - 2024-06-17T03_21_00Z.html", "call"),
        ("Diana Prince - Voicemail - 2024-06-17T03_21_00Z.html", "voicemail"),
    ]

    all_passed = True
    for filename, expected_type in test_cases:
        detected_type = extractor.determine_file_type(filename)
        if detected_type == expected_type:
            print(f"✅ {filename} -> {detected_type}")
        else:
            print(f"❌ {filename} -> Expected: {expected_type}, Got: {detected_type}")
            all_passed = False

    return all_passed


def test_unified_extraction():
    """Test the unified extraction method."""
    print("\n🧪 Testing unified extraction...")

    extractor = UnifiedExtractor()

    # Test with SMS content
    sms_html = """
    <html>
        <body>
            <div class="message">
                <abbr class="dt" title="2024-06-17T03:21:00Z">Jun 17</abbr>
                <cite><a href="tel:+15557776666">+15557776666</a></cite>
                <q>Test message</q>
            </div>
        </body>
    </html>
    """

    soup = create_test_html(sms_html)
    result = extractor.extract_all_info(
        "Jane Smith - Text - 2024-06-17T03_21_00Z.html", soup
    )

    if result:
        print(f"✅ Unified extraction successful:")
        print(f"   Type: {result.get('type')}")
        print(f"   Phone: {result.get('phone_number')}")
        print(f"   Content: {result.get('message_content')}")
    else:
        print("❌ Unified extraction failed")

    return result is not None


def main():
    """Run all tests."""
    print("🚀 Starting Unified Extractor Tests\n")

    tests = [
        test_sms_extraction,
        test_call_extraction,
        test_voicemail_extraction,
        test_automatic_type_detection,
        test_unified_extraction,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
