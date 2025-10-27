"""
Real-world scenario tests for conversation filtering.

These tests validate the filtering system against actual conversation patterns
found in Google Voice exports, ensuring the system correctly identifies and
handles real spam/commercial conversations while protecting legitimate ones.

Test Coverage:
- Political spam campaigns (real donation messages)
- Delivery notification spam (Door Dash-style high volume)
- Protected conversations with legal keywords
- Mixed spam/personal conversations
- 2FA/verification code conversations
- Medical billing notifications

Author: Claude Code
Date: 2025-10-26
"""

import pytest
import json
import tempfile
from pathlib import Path

from core.keyword_protection import KeywordProtection
from core.conversation_filter import ConversationFilter


@pytest.fixture
def keyword_protection():
    """Create keyword protection with realistic legal keywords."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        keywords_data = {
            "case_sensitive": False,
            "match_partial": True,
            "keywords": {
                "people": ["Mike Daddio", "Ed Harbur", "Phil Penney"],
                "companies": ["CSHC", "Harb Const"],
                "financial": ["$50,000", "$100,000", "invoice", "payment"],
                "legal": ["incident", "property damage", "settlement"]
            },
            "regex_patterns": [
                "INV\\d{4,}",  # Invoice numbers
                "\\$\\d{4,}"   # Dollar amounts $1000+
            ]
        }
        json.dump(keywords_data, f)
        keywords_file = Path(f.name)

    protection = KeywordProtection(keywords_file)
    yield protection
    keywords_file.unlink()  # Cleanup


class TestPoliticalSpamScenarios:
    """Test real political spam patterns."""

    def test_kamala_donation_campaign(self, keyword_protection):
        """
        Real example: Political campaign with donation matching.

        Pattern: "HUGE 700% MATCH to stand with Kamala. Donate now!"
        Should archive: Yes (political campaign, 0.92 confidence)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {
                "text": "HUGE 700% MATCH to stand with Kamala. Donate now!",
                "sender": "+12025551234",
                "timestamp": 1000
            },
            {
                "text": "Your donation will be 7X matched until midnight!",
                "sender": "+12025551234",
                "timestamp": 2000
            },
            {
                "text": "This is your last chance - DONATE NOW!",
                "sender": "+12025551234",
                "timestamp": 3000
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+12025551234",
            has_alias=False
        )

        assert should_archive is True
        assert confidence == 0.92
        assert "political" in reason.lower() or "campaign" in reason.lower()



class TestDeliverySpamScenarios:
    """Test real delivery notification spam."""

    def test_doordash_high_volume_spam(self, keyword_protection):
        """
        Real example: DoorDash high-volume delivery notifications (400+ messages).

        Pattern: Repetitive "order has been picked up", "Dasher is on the way"
        Should archive: Yes (high-volume delivery, 0.97 confidence)
        """
        filter = ConversationFilter(keyword_protection)

        # Simulate 60 delivery notifications (no user replies)
        messages = []
        for i in range(60):
            messages.append({
                "text": f"Your DoorDash order has been picked up - Order #{i}",
                "sender": "+15551234567",
                "timestamp": 1000 + i
            })

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+15551234567",
            has_alias=False
        )

        assert should_archive is True
        assert confidence == 0.97
        assert "delivery" in reason.lower()

    def test_uber_eats_notifications(self, keyword_protection):
        """
        Real example: Uber Eats delivery tracking.

        Pattern: "Your order is on the way", tracking updates
        Should archive: Yes (delivery notification, 0.97 confidence)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {"text": "Your Uber Eats order is being prepared", "sender": "+15551234567", "timestamp": 1000},
            {"text": "Your order has been picked up", "sender": "+15551234567", "timestamp": 2000},
            {"text": "Dasher is on the way - track your order", "sender": "+15551234567", "timestamp": 3000},
            {"text": "Your order has been delivered", "sender": "+15551234567", "timestamp": 4000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+15551234567",
            has_alias=False
        )

        assert should_archive is True
        assert confidence == 0.97


class TestProtectedLegalConversations:
    """Test real legal case conversations that should be protected."""

    def test_contractor_conversation_protected(self, keyword_protection):
        """
        Real example: Conversation with Ed Harbur (contractor) about property incident.

        Keywords: "Ed Harbur", "CSHC", "property damage"
        Should archive: No (protected by keywords)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {"text": "Ed - the incident report is ready", "sender": "Me", "timestamp": 1000},
            {"text": "Thanks, I'll review it tonight", "sender": "Ed_Harbur", "timestamp": 2000},
            {"text": "CSHC will handle the property damage claim", "sender": "Me", "timestamp": 3000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "Ed_Harbur",  # Conversation ID matches keyword
            has_alias=True
        )

        assert should_archive is False
        assert confidence == 1.0
        assert "protected" in reason.lower()
        assert "Ed Harbur" in reason

    def test_invoice_conversation_protected(self, keyword_protection):
        """
        Real example: Invoice discussion with contractor.

        Pattern: Contains invoice number "INV01923-456" and dollar amounts
        Should archive: No (protected by regex pattern)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {"text": "Invoice INV01923-456 for the repair work", "sender": "Mike_Daddio", "timestamp": 1000},
            {"text": "Total is $50,000 for materials and labor", "sender": "Mike_Daddio", "timestamp": 2000},
            {"text": "Payment due by end of month", "sender": "Mike_Daddio", "timestamp": 3000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "Mike_Daddio",
            has_alias=True
        )

        # Should be protected by EITHER "Mike Daddio" keyword OR INV regex OR $50,000 regex
        assert should_archive is False
        assert confidence == 1.0
        assert "protected" in reason.lower()


class Test2FAVerificationScenarios:
    """Test real 2FA/verification code scenarios."""

    def test_google_verification_code(self, keyword_protection):
        """
        Real example: Google verification code text.

        Pattern: "Your verification code is 123456"
        Should archive: Yes (2FA code, 0.98 confidence)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {"text": "Your verification code is 123456", "sender": "+15551234567", "timestamp": 1000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+15551234567",
            has_alias=False
        )

        assert should_archive is True
        assert confidence == 0.98
        assert "2fa" in reason.lower() or "verification" in reason.lower()

    def test_bank_security_code(self, keyword_protection):
        """
        Real example: Bank security code for transaction verification.

        Pattern: "Security code: 789012 for your transaction"
        Should archive: Yes (2FA/security code, 0.98 confidence)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {"text": "Security code: 789012 for your transaction", "sender": "+18005551234", "timestamp": 1000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+18005551234",
            has_alias=False
        )

        assert should_archive is True
        assert confidence == 0.98


class TestMedicalBillingScenarios:
    """Test real medical billing notification scenarios."""

    def test_physician_bill_notification(self):
        """
        Real example: Medical billing notification from toll-free number.

        Pattern: 866 toll-free number + "bill is ready"
        Should archive: Yes (medical billing, 0.88 confidence)

        Note: Uses minimal keywords to avoid false protection
        """
        # Create keyword protection without financial keywords
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            keywords_data = {
                "case_sensitive": False,
                "match_partial": True,
                "keywords": {
                    "people": ["Alice", "Bob"]  # Simple names, no financial terms
                },
                "regex_patterns": []
            }
            json.dump(keywords_data, f)
            keywords_file = Path(f.name)

        protection = KeywordProtection(keywords_file)
        filter = ConversationFilter(protection)

        messages = [
            {"text": "Your bill is ready to view online", "sender": "+18661234567", "timestamp": 1000},
            {"text": "Ok", "sender": "Me", "timestamp": 1800000},  # 30 min later
            {"text": "Log in to patient portal for details", "sender": "+18661234567", "timestamp": 3600001},  # >1 hour from start
            {"text": "Payment is due within 30 days", "sender": "+18661234567", "timestamp": 3600002}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+18661234567",
            has_alias=False
        )

        # Cleanup
        keywords_file.unlink()

        assert should_archive is True
        assert confidence == 0.88
        assert "medical" in reason.lower() or "billing" in reason.lower() or "toll-free" in reason.lower()


class TestStopOnlyScenarios:
    """Test real STOP-only orphan message scenarios."""

    def test_single_stop_message(self, keyword_protection):
        """
        Real example: Single "Stop" message sent to unsubscribe.

        Context: User sent "Stop" to end spam, no other messages
        Should archive: Yes (STOP-only orphan, 0.96 confidence)
        """
        filter = ConversationFilter(keyword_protection)

        messages = [
            {"text": "Stop", "sender": "Me", "timestamp": 1000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "+15551234567",
            has_alias=False
        )

        assert should_archive is True
        assert confidence == 0.96
        assert "stop" in reason.lower() or "orphan" in reason.lower()


class TestMixedScenarios:
    """Test conversations with mixed characteristics."""

    def test_spam_with_protected_keyword_in_filename(self, keyword_protection):
        """
        Edge case: Conversation ID contains partial match of protected keyword.

        Scenario: "Mike_Daddio_Construction" contains "Mike Daddio" keyword
        Should archive: No (protected by keyword in filename)
        """
        filter = ConversationFilter(keyword_protection)

        # Spam message but conversation ID contains protected keyword
        messages = [
            {"text": "Your verification code is 123456", "sender": "+15551234567", "timestamp": 1000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages,
            "Mike_Daddio_Construction",  # Contains "Mike Daddio" keyword
            has_alias=True
        )

        # Should be protected because conversation ID contains "Mike Daddio"
        assert should_archive is False
        assert confidence == 1.0
        assert "protected" in reason.lower()
        assert "Mike Daddio" in reason
