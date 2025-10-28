"""
Unit tests for conversation filtering patterns.

This module tests all 15 filtering patterns plus protected-first architecture
and edge cases for the conversation filtering system.

Test Coverage:
- Very Safe Patterns (0.95-0.98): 2FA, delivery, STOP, appointments, banking
- Safe Patterns (0.85-0.94): Political, marketing, medical, surveys, templates
- Aggressive Patterns (0.75-0.84): One-way, short-lived, link-heavy, no-alias, noreply
- Protected-First Architecture (validates keyword protection bypasses filters)
- Confidence scoring and thresholds
- Edge cases

Author: Claude Code
Date: 2025-10-26
"""

import pytest
import tempfile
import json
from pathlib import Path

from core.conversation_filter import ConversationFilter
from core.keyword_protection import KeywordProtection


# Test fixture for keyword protection
@pytest.fixture
def keyword_protection(tmp_path):
    """Create test keyword protection instance."""
    keywords_file = tmp_path / "test_keywords.json"
    keywords_data = {
        "case_sensitive": False,
        "match_partial": True,
        "keywords": {
            "people": ["Mike Daddio", "Ed Harbur"]
        },
        "regex_patterns": []
    }
    keywords_file.write_text(json.dumps(keywords_data))
    return KeywordProtection(keywords_file)


class TestVerySafePatterns:
    """Test very safe filtering patterns (confidence 0.95-0.98)."""

    def test_2fa_verification_codes(self, keyword_protection):
        """Pattern 1: 2FA/verification codes (0.98 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # Test verification code pattern
        messages = [{"text": "Your verification code is 123456", "sender": "+15551234567", "timestamp": 1000}]
        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "2FA" in reason or "verification" in reason.lower()
        assert confidence == 0.98

    def test_delivery_notifications(self, keyword_protection):
        """Pattern 2: Delivery notifications (0.97 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # Test high-volume delivery notifications (50+ messages, 0 replies)
        messages = [
            {"text": f"Your order has been picked up - delivery {i}", "sender": "+15551234567", "timestamp": 1000 + i}
            for i in range(60)
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "delivery" in reason.lower()
        assert confidence == 0.97

    def test_stop_only_messages(self, keyword_protection):
        """Pattern 3: STOP-only messages (0.96 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # Single message: "Stop"
        messages = [{"text": "Stop", "sender": "Me", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "STOP" in reason or "orphan" in reason
        assert confidence == 0.96

    def test_appointment_reminders(self, keyword_protection):
        """Pattern 4: Appointment reminders (0.95 confidence)."""
        filter = ConversationFilter(keyword_protection)

        messages = [{"text": "Reminder: Your appointment on 12/15 at 3pm", "sender": "+15551234567", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "appointment" in reason.lower() or "reminder" in reason.lower()
        assert confidence == 0.95

    def test_appointment_reminders_one_medical_style(self, keyword_protection):
        """Pattern 4: One Medical style appointment reminders (Bug fix for +14159428664)."""
        filter = ConversationFilter(keyword_protection)

        # Real One Medical message that was previously missed
        messages = [
            {
                "text": "Hi Nicholas, this is a message about your upcoming appointment at One Medical.\n\n"
                       "You have an appointment on Wed, April 26 at 8:00 AM EDT at 5 Columbus Circle, Suite 1802, New York, NY 10019 with Paul.\n\n"
                       "To Confirm: Reply Y\nTo Reschedule: https://app.onemedical.com/appointments/list?nid=2095802\nTo Cancel: Reply N",
                "sender": "+14159428664",
                "timestamp": 1000
            },
            {"text": "Y", "sender": "Me", "timestamp": 1001},
            {
                "text": "Great, see you on Wednesday, 4/26/23, at 8:00 AM EDT! Save time during your appointment by checking in with the One Medical Mobile app - www.onemedical.com/technology",
                "sender": "+14159428664",
                "timestamp": 1002
            },
            {
                "text": "Hi Nicholas, you have an appointment today at 8:00 AM EDT at 5 Columbus Circle, Suite 1802, New York, NY 10019 with Paul. Please arrive 5 mins early.\n\n"
                       "To Reschedule: https://app.onemedical.com/appointments/list?nid=2107835\nTo Cancel: Reply N\n\nRunning late? Reply LATE",
                "sender": "+14159428664",
                "timestamp": 1003
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+14159428664", has_alias=False
        )

        assert should_archive is True, "One Medical appointment reminders should be archived"
        assert "appointment" in reason.lower(), f"Expected 'appointment' in reason, got: {reason}"
        assert confidence == 0.95

    def test_appointment_reminders_bond_vet_style(self, keyword_protection):
        """Pattern 4: Bond Vet style appointment reminders (Bug fix for +16469801675)."""
        filter = ConversationFilter(keyword_protection)

        # Real Bond Vet messages that were previously missed
        messages = [
            {
                "text": "Bond Vet: Hi Nicholas, this is a reminder that Hazel's appointment at "
                       "Bond Vet - Hell's Kitchen is coming up on Monday, April 29 at 11:00AM\n\n"
                       "Please respond with 'Confirm' to confirm your visit.",
                "sender": "+16469801675",
                "timestamp": 1000
            },
            {
                "text": "Confirm",
                "sender": "Me",
                "timestamp": 1001
            },
            {
                "text": "Bond Vet: Hi Nicholas, Hazel is confirmed for an appointment at "
                       "Bond Vet - Hell's Kitchen on Monday, April 29 at 11:00 AM.\n\n"
                       "Need to make a change? Manage your visit here: https://bondvet.com/reschedule",
                "sender": "+16469801675",
                "timestamp": 1002
            },
            {
                "text": "Bond Vet: Thank you for bringing your pet to Bond Vet. "
                       "How likely are you to recommend Bond Vet to a fellow pet parent? "
                       "Please reply with a number from 0 to 10.",
                "sender": "+16469801675",
                "timestamp": 1003
            },
            {
                "text": "8",
                "sender": "Me",
                "timestamp": 1004
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+16469801675", has_alias=False
        )

        assert should_archive is True, "Bond Vet appointment reminders should be archived"
        assert "appointment" in reason.lower(), f"Expected 'appointment' in reason, got: {reason}"
        assert confidence == 0.95

    def test_delivery_notifications_subscription_services(self, keyword_protection):
        """Pattern 2: Subscription delivery services like Ollie (Bug fix for +16463498598)."""
        filter = ConversationFilter(keyword_protection)

        # Real Ollie dog food subscription messages that were previously missed
        messages = [
            {
                "text": "Ollie: Hazel's box is on the way! 🚚 \nOrder #: 2070968\n"
                       "Track your order: https://myollie.com/account/tracking/",
                "sender": "+16463498598",
                "timestamp": 1000
            },
            {
                "text": "Ollie: Hazel's box has arrived! \n\nOrder #: 2070968\n"
                       "Delivered On: Feb 24, 2024 04:22 PM\n\n"
                       "Rate your delivery experience: https://olliepets.typeform.com/to/K7OysUJf",
                "sender": "+16463498598",
                "timestamp": 1001
            },
            {
                "text": "Ollie: Hazel's box ships soon\n\n"
                       "Need to make a change?\nUpdate your plan on your account",
                "sender": "+16463498598",
                "timestamp": 1002
            },
            {
                "text": "Ollie: Hazel's box is packed and ready to go! 🚚 \n"
                       "Order #: 3124518\nTrack your order: https://myollie.com/...",
                "sender": "+16463498598",
                "timestamp": 1003
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+16463498598", has_alias=False
        )

        assert should_archive is True, "Subscription delivery services like Ollie should be archived"
        assert "delivery" in reason.lower(), f"Expected 'delivery' in reason, got: {reason}"
        assert confidence == 0.97

    def test_banking_alerts(self, keyword_protection):
        """Pattern 5: Banking alerts (0.95 confidence)."""
        filter = ConversationFilter(keyword_protection)

        messages = [{"text": "Your account balance is $123.45", "sender": "+15551234567", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "banking" in reason.lower() or "account" in reason.lower()
        assert confidence == 0.95


class TestSafePatterns:
    """Test safe filtering patterns (confidence 0.85-0.94)."""

    def test_political_campaigns(self, keyword_protection):
        """Pattern 6: Political campaigns (0.92 confidence)."""
        filter = ConversationFilter(keyword_protection)

        messages = [{"text": "HUGE 700% MATCH to stand with Kamala. Donate now!", "sender": "+15551234567", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "political" in reason.lower() or "campaign" in reason.lower()
        assert confidence == 0.92

    def test_marketing_promotions(self, keyword_protection):
        """Pattern 7: Marketing promotions (0.90 confidence)."""
        filter = ConversationFilter(keyword_protection)

        messages = [{"text": "FLASH SALE: 50% OFF - Limited time offer!", "sender": "+15551234567", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "marketing" in reason.lower() or "promotion" in reason.lower()
        assert confidence == 0.90

    def test_medical_billing(self, keyword_protection):
        """Pattern 8: Medical billing (0.88 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # Toll-free number (866) + billing keywords
        # Need 3+ messages to avoid short-lived pattern, and user reply to avoid one-way broadcast
        # Pattern requires "bill is ready" format (no words between "is" and "ready")
        messages = [
            {"text": "Your bill is ready to view", "sender": "+18661234567", "timestamp": 1000},
            {"text": "Ok", "sender": "Me", "timestamp": 1500},  # User reply avoids one-way broadcast
            {"text": "Payment is due in 30 days", "sender": "+18661234567", "timestamp": 2000},
            {"text": "Visit patient portal for details", "sender": "+18661234567", "timestamp": 3000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+18661234567", has_alias=False
        )

        assert should_archive is True
        assert "medical" in reason.lower() or "billing" in reason.lower() or "toll-free" in reason.lower()
        assert confidence == 0.88

    def test_survey_polls(self, keyword_protection):
        """Pattern 9: Surveys/polls (0.87 confidence)."""
        filter = ConversationFilter(keyword_protection)

        messages = [{"text": "Live Survey: Do you approve of the president?", "sender": "+15551234567", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "survey" in reason.lower() or "poll" in reason.lower()
        assert confidence == 0.87

    def test_automated_booking_chatbot(self, keyword_protection):
        """Pattern 9b: Automated booking/scheduling chatbots (Bug fix for +16468256493)."""
        filter = ConversationFilter(keyword_protection)

        # Real Dermatology Specialists automated booking system messages
        messages = [
            {
                "text": "Thank you for calling The Dermatology Specialists! We're sorry about the wait. "
                       "You can book, reschedule, or cancel appointments through this 24/7 text-only number.",
                "sender": "+16468256493",
                "timestamp": 1000
            },
            {
                "text": "Which location or provider are you interested in? If you're unsure, please provide "
                       "your zip code or neighborhood, and we'll suggest options for you. Additionally, let "
                       "us know if you're looking for a virtual appointment.",
                "sender": "+16468256493",
                "timestamp": 1001
            },
            {
                "text": "We had a follow up appointment for today but the doctor said to get an ultrasound...",
                "sender": "Me",
                "timestamp": 1002
            },
            {
                "text": "Your request would be best handled by our dedicated support staff. "
                       "Kindly call their direct line at (917) 473-3497.",
                "sender": "+16468256493",
                "timestamp": 1003
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+16468256493", has_alias=False
        )

        assert should_archive is True, "Automated booking chatbots should be archived"
        assert "booking" in reason.lower() or "chatbot" in reason.lower(), f"Expected 'booking' or 'chatbot' in reason, got: {reason}"
        assert confidence == 0.87

    def test_template_messages(self, keyword_protection):
        """Pattern 10: Template/duplicate messages (0.85 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # 10 messages, 8 identical (>50%)
        messages = [
            {"text": "Exact same message", "sender": "+15551234567", "timestamp": 1000 + i}
            for i in range(8)
        ] + [
            {"text": "Different message 1", "sender": "+15551234567", "timestamp": 1008},
            {"text": "Different message 2", "sender": "+15551234567", "timestamp": 1009}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "template" in reason.lower() or "duplicate" in reason.lower()
        assert confidence == 0.85

    def test_template_messages_progressive_threshold(self, keyword_protection):
        """Pattern 10: Template messages with progressive threshold (short conversations)."""
        filter = ConversationFilter(keyword_protection)

        # Short conversation (6 messages < 10): 4 unique, 2 duplicates = 33.3% duplicates
        # Progressive threshold: < 10 messages needs only 25% duplicates to trigger
        messages = [
            {"text": "Message 1", "sender": "+16468256493", "timestamp": 1000},
            {"text": "Message 2", "sender": "+16468256493", "timestamp": 1001},
            {"text": "User reply", "sender": "Me", "timestamp": 1002},
            {"text": "Message 3", "sender": "+16468256493", "timestamp": 1003},
            {"text": "Message 1", "sender": "+16468256493", "timestamp": 1004},  # Duplicate
            {"text": "Message 2", "sender": "+16468256493", "timestamp": 1005},  # Duplicate
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+16468256493", has_alias=False
        )

        assert should_archive is True, "Short conversations with 33.3% duplicates should be archived (25% threshold)"
        assert "template" in reason.lower() or "duplicate" in reason.lower(), f"Expected 'template' or 'duplicate' in reason, got: {reason}"
        assert "33%" in reason, f"Expected duplicate percentage in reason, got: {reason}"
        assert confidence == 0.85

    def test_real_estate_services(self, keyword_protection):
        """Pattern 10b: Real estate commercial services (Bug fix for +16469339052)."""
        filter = ConversationFilter(keyword_protection)

        # Real Compass Collections real estate message
        messages = [
            {
                "text": "📞 Incoming call from Unknown (Duration: 06:55)",
                "sender": "+16469339052",
                "timestamp": 1000
            },
            {
                "text": "Hi! Just wanted to let you know that I sent Susan an invite to Compass Collections. :)",
                "sender": "+16469339052",
                "timestamp": 1001
            },
            {
                "text": "Ok great thanks",
                "sender": "Me",
                "timestamp": 1002
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+16469339052", has_alias=False
        )

        assert should_archive is True, "Real estate commercial services should be archived"
        assert "real estate" in reason.lower(), f"Expected 'real estate' in reason, got: {reason}"
        assert confidence == 0.85

    def test_real_estate_user_initiated_inquiry(self, keyword_protection):
        """Pattern 10b: User-initiated real estate inquiry (Bug fix for +17187755287)."""
        filter = ConversationFilter(keyword_protection)

        # User asking about apartment availability, brief response
        messages = [
            {
                "text": "Hi just checking to see if 340 w 86th 9a is still available",
                "sender": "Me",
                "timestamp": 1000
            },
            {
                "text": "No there's a pending application",
                "sender": "+17187755287",
                "timestamp": 1001
            },
            {
                "text": "Ok thanks for the response",
                "sender": "Me",
                "timestamp": 1002
            }
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+17187755287", has_alias=False
        )

        assert should_archive is True, "User-initiated real estate inquiry should be archived"
        assert "real estate" in reason.lower(), f"Expected 'real estate' in reason, got: {reason}"
        assert confidence == 0.85


class TestAggressivePatterns:
    """Test aggressive filtering patterns (confidence 0.75-0.84)."""

    def test_one_way_broadcast(self, keyword_protection):
        """Pattern 11: One-way broadcast (0.82 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # 5 messages from sender, 0 replies
        messages = [
            {"text": f"Message {i}", "sender": "+15551234567", "timestamp": 1000 + i}
            for i in range(5)
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "one-way" in reason.lower() or "broadcast" in reason.lower()
        assert confidence == 0.82

    def test_short_lived_conversation(self, keyword_protection):
        """Pattern 12: Short-lived conversation (0.80 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # 2 messages within 30 minutes (< 1 hour)
        messages = [
            {"text": "Hi", "sender": "Me", "timestamp": 1000},
            {"text": "Hello", "sender": "+15551234567", "timestamp": 1000 + (30 * 60 * 1000)}  # 30 min later
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "short" in reason.lower() or "hour" in reason.lower()
        assert confidence == 0.80

    def test_link_heavy_messages(self, keyword_protection):
        """Pattern 13: Link-heavy messages (0.78 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # 5 messages, 4 with links (80% > 75% threshold)
        # Include user reply to avoid one-way broadcast pattern
        messages = [
            {"text": "Check this out https://example.com/1", "sender": "+15551234567", "timestamp": 1000},
            {"text": "Also https://example.com/2", "sender": "+15551234567", "timestamp": 1001},
            {"text": "Thanks", "sender": "Me", "timestamp": 1002},  # User reply avoids one-way broadcast
            {"text": "And https://example.com/3", "sender": "+15551234567", "timestamp": 1003},
            {"text": "Final link https://example.com/4", "sender": "+15551234567", "timestamp": 1004}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "link" in reason.lower() or "url" in reason.lower()
        assert confidence == 0.78

    def test_minimal_engagement(self, keyword_protection):
        """Pattern 17b: Minimal engagement (brief acknowledgments only)."""
        filter = ConversationFilter(keyword_protection)

        # 6 messages: 5 from sender, 1 brief user reply
        messages = [
            {"text": "Hey, we have a new offer for you!", "sender": "+15551234567", "timestamp": 1000},
            {"text": "It's about our premium service", "sender": "+15551234567", "timestamp": 1001},
            {"text": "Ok great thanks", "sender": "Me", "timestamp": 1002},  # Brief acknowledgment
            {"text": "Let me know if you want details", "sender": "+15551234567", "timestamp": 1003},
            {"text": "We can schedule a call", "sender": "+15551234567", "timestamp": 1004},
            {"text": "Looking forward to hearing from you", "sender": "+15551234567", "timestamp": 1005}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True, "Minimal engagement conversations should be archived"
        assert "minimal engagement" in reason.lower() or "brief" in reason.lower(), f"Expected 'minimal engagement' in reason, got: {reason}"
        assert confidence == 0.78

    def test_no_alias_commercial_keywords(self, keyword_protection):
        """Pattern 14: No alias + commercial keywords (0.76 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # Need 3+ messages to avoid short-lived pattern, and user reply to avoid one-way broadcast
        messages = [
            {"text": "To unsubscribe from our list, reply STOP", "sender": "+15551234567", "timestamp": 1000},
            {"text": "Ok", "sender": "Me", "timestamp": 1500},  # User reply avoids one-way broadcast
            {"text": "Msg&data rates may apply", "sender": "+15551234567", "timestamp": 2000},
            {"text": "For customer service, call 1-800-...", "sender": "+15551234567", "timestamp": 3000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False  # No alias
        )

        assert should_archive is True
        assert "no alias" in reason.lower() or "commercial" in reason.lower()
        assert confidence == 0.76

    def test_noreply_pattern(self, keyword_protection):
        """Pattern 15: No-reply pattern (0.75 confidence)."""
        filter = ConversationFilter(keyword_protection)

        # Need 3+ messages to avoid short-lived pattern, and user reply to avoid one-way broadcast
        # Use has_alias=True to avoid no-alias pattern (which would match "do not reply" commercial keyword)
        messages = [
            {"text": "This is an automated message. Do not reply.", "sender": "+15551234567", "timestamp": 1000},
            {"text": "Got it", "sender": "Me", "timestamp": 1500},  # User reply avoids one-way broadcast
            {"text": "Your request has been processed", "sender": "+15551234567", "timestamp": 2000},
            {"text": "This mailbox is not monitored", "sender": "+15551234567", "timestamp": 3000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=True  # Has alias to skip no-alias pattern
        )

        assert should_archive is True
        assert "no-reply" in reason.lower() or "automated" in reason.lower()
        assert confidence == 0.75


class TestProtectedFirstArchitecture:
    """Test protected-first architecture and keyword protection integration."""

    def test_protected_bypasses_all_filters(self, keyword_protection):
        """
        Critical test: Protected conversations bypass ALL filtering patterns.

        This validates the protected-first architecture where keyword protection
        is checked BEFORE any filtering patterns.
        """
        filter = ConversationFilter(keyword_protection)

        # Message that matches STOP pattern (0.96 confidence)
        # BUT also matches "Mike Daddio" keyword - should be PROTECTED
        messages = [{"text": "Stop bothering Mike Daddio", "sender": "Me", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "Mike_Daddio", has_alias=True
        )

        # Should be protected, NOT archived
        assert should_archive is False
        assert "protected" in reason.lower()
        assert "Mike Daddio" in reason
        assert confidence == 1.0  # Protection has maximum confidence

    def test_protected_by_filename_only(self, keyword_protection):
        """Test protection by conversation ID (filename) without keyword in text."""
        filter = ConversationFilter(keyword_protection)

        # Message would be archived (short-lived), but conversation ID matches keyword
        messages = [{"text": "Ok", "sender": "Me", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "Ed_Harbur", has_alias=True
        )

        # Should be protected by filename match
        assert should_archive is False
        assert "protected" in reason.lower()
        assert confidence == 1.0


class TestConfidenceAndEdgeCases:
    """Test confidence scoring, thresholds, and edge cases."""

    def test_confidence_scoring_correct(self, keyword_protection):
        """Test that each pattern returns correct confidence score."""
        filter = ConversationFilter(keyword_protection)

        # 2FA should return 0.98 (needs "verification code" keyword to match pattern)
        messages = [{"text": "Your verification code is 123456", "sender": "+15551234567", "timestamp": 1000}]
        _, _, confidence = filter.should_archive_conversation(messages, "+15551234567", False)
        assert confidence == 0.98

        # Political should return 0.92 (needs 3+ messages to avoid short-lived)
        messages = [
            {"text": "Donate to support our campaign", "sender": "+15551234567", "timestamp": 1000},
            {"text": "Join us in making a difference", "sender": "+15551234567", "timestamp": 2000},
            {"text": "Every contribution helps", "sender": "+15551234567", "timestamp": 3000}
        ]
        _, _, confidence = filter.should_archive_conversation(messages, "+15551234567", False)
        assert confidence == 0.92

    def test_first_match_wins(self, keyword_protection):
        """Test that first matching pattern wins (patterns evaluated in order)."""
        filter = ConversationFilter(keyword_protection)

        # Message matches both 2FA (0.98) and noreply (0.75)
        # Should return 2FA since it's evaluated first
        messages = [{"text": "Your verification code is 123456. Do not reply.", "sender": "+15551234567", "timestamp": 1000}]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        assert should_archive is True
        assert "2FA" in reason or "verification" in reason.lower()
        assert confidence == 0.98  # Higher confidence pattern wins

    def test_no_filter_matches(self, keyword_protection):
        """Test that conversations not matching any filter are kept."""
        filter = ConversationFilter(keyword_protection)

        # Normal conversation - doesn't match any filter
        messages = [
            {"text": "Hey, how are you?", "sender": "Me", "timestamp": 1000},
            {"text": "I'm good, thanks!", "sender": "+15551234567", "timestamp": 2000},
            {"text": "Want to grab coffee tomorrow?", "sender": "Me", "timestamp": 3000}
        ]

        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=True
        )

        assert should_archive is False
        assert "no filter matched" in reason.lower()
        assert confidence == 0.0

    def test_get_stats_method(self, keyword_protection):
        """Test get_stats() returns correct filter statistics."""
        filter = ConversationFilter(keyword_protection)
        stats = filter.get_stats()

        # Updated: Now 18 patterns after adding Patterns 16, 17, 18
        assert stats["total_patterns"] == 18
        assert stats["very_safe_patterns"] == 5
        assert stats["safe_patterns"] == 5  # Pattern 18 is classified as aggressive, not safe
        assert stats["aggressive_patterns"] == 8  # Added Patterns 16, 17, and 18
        assert stats["keyword_protection_enabled"] is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_messages_list(self, keyword_protection):
        """Test handling of empty messages list."""
        filter = ConversationFilter(keyword_protection)

        messages = []
        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        # Empty conversations can't match patterns
        assert should_archive is False

    def test_filter_without_keyword_protection(self):
        """Test filter works without keyword protection (None)."""
        filter = ConversationFilter(keyword_protection=None)

        messages = [{"text": "Your verification code is 123456", "sender": "+15551234567", "timestamp": 1000}]
        should_archive, reason, confidence = filter.should_archive_conversation(
            messages, "+15551234567", has_alias=False
        )

        # Should still filter without keyword protection
        assert should_archive is True
        assert confidence == 0.98
