"""
Unit tests for Bug #30: T9 Conversion of Hash Strings Creates Malformed Phone Numbers.

Root cause: phonenumbers.parse() performs T9 conversion on hash strings like
"UN_HrTvGduCP140vxEc8laxag", converting letters to digits and creating malformed
phone numbers like "+1408932852924" (13 digits instead of 11 for US).

This test suite ensures:
1. Hash strings are NOT parsed as phone numbers
2. US phone numbers are validated for exactly 11 digits
3. Type system correctly declares Union[str, int] return types
4. Empty tel: links in Google Voice exports are handled gracefully
"""

import pytest
from bs4 import BeautifulSoup


def test_hash_strings_not_parsed_as_phone_numbers():
    """
    Test that UN_... hash strings don't get T9-converted to phone numbers.

    Bug scenario:
    - File: "Aniella Tang - Text - 2021-04-10T00_40_26Z.html"
    - Empty tel: links in HTML
    - Fallback Strategy 4 returns hash: "UN_HrTvGduCP140vxEc8laxag"
    - phonenumbers.parse() converts via T9: U=8, N=6, H=4, r=7...
    - Result: "+1408932852924" (13 digits - malformed!)

    Expected: Hash strings should be used directly as conversation IDs,
    not parsed by phonenumbers library.
    """
    from sms import get_first_phone_number

    # Empty messages (will trigger fallback)
    messages = []

    # Hash string as fallback (from Strategy 4)
    hash_fallback = "UN_HrTvGduCP140vxEc8laxag"
    own_number = "+13474106066"

    # Should return hash string directly, NOT T9-convert it
    phone_number, participant = get_first_phone_number(messages, hash_fallback, own_number)

    # Should return the hash string as-is (valid conversation ID)
    assert phone_number == hash_fallback, \
        f"Hash {hash_fallback} should be returned as-is. Got: {phone_number}"

    # Should not be converted to malformed 13-digit number
    assert phone_number != "+1408932852924", \
        "Hash should not be T9-converted to malformed phone number"

    # Participant should be created with appropriate label
    assert participant is not None, "Participant should be created for hash-based ID"
    participant_html = str(participant)
    assert "Unknown (Name-based)" in participant_html or "Unknown" in participant_html, \
        "Participant should indicate name-based conversation"


def test_is_valid_us_phone_number():
    """
    Test US phone number validation (11 digits exactly).

    US phone numbers: +1 (country code) + 10 digits = 11 total
    Bug: System accepted 13-digit malformed numbers
    """
    from sms import is_valid_us_phone_number

    # Valid US numbers (11 digits: +1 + 10 digits)
    assert is_valid_us_phone_number("+13478736042") is True, \
        "Valid 11-digit US number should pass"
    assert is_valid_us_phone_number("13478736042") is True, \
        "Valid 11-digit US number without + should pass"
    assert is_valid_us_phone_number(13478736042) is True, \
        "Valid 11-digit US number as int should pass"

    # Invalid: 13 digits (malformed - from T9 bug)
    assert is_valid_us_phone_number("+1408932852924") is False, \
        "Malformed 13-digit number should be rejected"
    assert is_valid_us_phone_number("1408932852924") is False, \
        "Malformed 13-digit number without + should be rejected"
    assert is_valid_us_phone_number(1408932852924) is False, \
        "Malformed 13-digit number as int should be rejected"

    # Invalid: Too short
    assert is_valid_us_phone_number("+133") is False, \
        "Too-short number should be rejected"
    assert is_valid_us_phone_number("1408") is False, \
        "Partial number should be rejected"

    # Invalid: Not starting with 1 (non-US)
    assert is_valid_us_phone_number("+44207946") is False, \
        "Non-US country code should be rejected"

    # Invalid: Hash strings
    assert is_valid_us_phone_number("UN_HrTvGduCP140vxEc8laxag") is False, \
        "Hash strings should be rejected"

    # Edge cases
    assert is_valid_us_phone_number(0) is False, "Zero should be rejected"
    assert is_valid_us_phone_number(None) is False, "None should be rejected"
    assert is_valid_us_phone_number("") is False, "Empty string should be rejected"


def test_extract_fallback_returns_union_type():
    """
    Test that extract_fallback_number_cached can return str or int.

    Bug: Function signature said 'int' but returned 'str' for hash strings.
    Fix: Signature now Union[str, int] to be honest about return types.
    """
    from sms import extract_fallback_number_cached

    # Name-based file returns hash (str)
    result1 = extract_fallback_number_cached(
        "Susan Nowak Tang - Text - 2024-01-01T00_00_00Z.html"
    )
    # Should be either int or str, but if str, should be hash format
    if isinstance(result1, str):
        assert result1.startswith("UN_"), \
            f"String return should be hash format: {result1}"

    # Number-based file returns int
    result2 = extract_fallback_number_cached(
        "+13478736042 - Text - 2024-01-01T00_00_00Z.html"
    )
    assert isinstance(result2, int), \
        f"Expected int from number filename: {result2}"
    assert result2 == 13478736042, \
        f"Expected 13478736042, got {result2}"

    # Numeric code at start returns int
    result3 = extract_fallback_number_cached(
        "22891 - Text - 2024-01-01T00_00_00Z.html"
    )
    assert isinstance(result3, int), \
        f"Expected int from numeric code: {result3}"
    assert result3 == 22891, \
        f"Expected 22891, got {result3}"


def test_empty_tel_links_use_fallback():
    """
    Test that files with empty tel: links trigger proper fallback handling.

    Google Voice bug: Some exports have <a class="tel" href="tel:">
    This triggered the malformed phone number generation bug.
    """
    from sms import get_first_phone_number

    html = '''
    <div class="message">
        <cite class="sender vcard">
            <a class="tel" href="tel:"><span class="fn"></span></a>
        </cite>
        <q>Test message</q>
    </div>
    '''

    soup = BeautifulSoup(html, "html.parser")
    messages = soup.find_all("div", class_="message")

    # With hash fallback - should return hash as-is
    phone_number, participant = get_first_phone_number(
        messages,
        fallback_number="UN_TestHashValue",
        own_number="+13474106066"
    )

    # Should use hash directly
    assert phone_number == "UN_TestHashValue", \
        f"Empty tel: links with hash fallback should use hash. Got: {phone_number}"

    # Should NOT be T9-converted
    assert not phone_number.startswith("+1"), \
        "Hash should not be converted to E.164 phone format"

    # With numeric fallback - behavior depends on validation
    phone_number2, _ = get_first_phone_number(
        messages,
        fallback_number=13478736042,
        own_number="+13474106066"
    )
    # Numeric fallback may be formatted or return 0 to trigger search
    # Key point: Should NOT be T9-converted to something invalid
    assert phone_number2 == "+13478736042" or phone_number2 == 0, \
        f"Numeric fallback should be formatted or return 0. Got: {phone_number2}"

    # Verify it's not malformed
    if isinstance(phone_number2, str):
        # Should be valid E.164 format
        assert phone_number2.startswith("+1"), \
            f"Formatted number should be E.164: {phone_number2}"
        assert len(phone_number2) == 12, \
            f"US number should be 12 chars (+1 + 10 digits): {phone_number2}"


def test_malformed_numbers_rejected_in_validation():
    """
    Test that malformed phone numbers are rejected during validation.

    Integration test ensuring the three-layer defense:
    1. Hash strings used directly (not parsed)
    2. Phone strings validated before parsing
    3. US numbers validated for digit count after parsing
    """
    from sms import get_first_phone_number

    # Empty messages
    messages = []
    own_number = "+13474106066"

    # Test 1: Hash string - should be used directly
    result1, _ = get_first_phone_number(messages, "UN_abc123", own_number)
    assert result1 == "UN_abc123", "Hash strings should pass through unchanged"

    # Test 2: Valid US number - should be formatted
    result2, _ = get_first_phone_number(messages, "13478736042", own_number)
    assert result2 == "+13478736042" or result2 == 0, \
        f"Valid US number should be formatted or trigger search. Got: {result2}"

    # Test 3: Empty/zero fallback - should return 0
    result3, _ = get_first_phone_number(messages, 0, own_number)
    assert result3 == 0, "Zero fallback should return 0"

    result4, _ = get_first_phone_number(messages, None, own_number)
    assert result4 == 0, "None fallback should return 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
