"""
Conversation filtering system for post-processing.

This module provides comprehensive filtering patterns to identify and archive
spam, commercial, political, and automated conversations while protecting
important personal communications through keyword matching.

Architecture: Protected-First
- Keyword protection is evaluated FIRST
- Protected conversations bypass ALL filtering patterns
- Confidence scoring (0.75-0.98) indicates filter reliability
- Returns actionable decisions with detailed reasoning

Filtering Patterns:
- Very Safe (0.95-0.98): 2FA codes, delivery notifications, STOP messages
- Safe (0.85-0.94): Political campaigns, marketing, medical billing
- Aggressive (0.75-0.84): Short interactions, no-reply patterns, time-based patterns
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import logging

from core.keyword_protection import KeywordProtection

logger = logging.getLogger(__name__)


class ConversationFilter:
    """
    Evaluates conversations for archiving based on multiple filtering patterns.

    Supports:
    - Protected-first keyword checking
    - 15 tiered filtering patterns
    - Confidence scoring
    - Detailed reasoning for filtering decisions
    """

    def __init__(self, keyword_protection: Optional[KeywordProtection] = None):
        """
        Initialize conversation filter.

        Args:
            keyword_protection: Optional KeywordProtection instance
                              If None, keyword protection is disabled
        """
        self.keyword_protection = keyword_protection

    def should_archive_conversation(
        self,
        messages: List[Dict[str, Any]],
        sender_phone: str,
        has_alias: bool
    ) -> Tuple[bool, str, float]:
        """
        Determine if conversation should be archived.

        Protected-First Architecture:
        1. Check keyword protection FIRST
        2. If protected, return False immediately
        3. Otherwise, evaluate filtering patterns

        Args:
            messages: List of message dicts with fields:
                     - text: Message content
                     - sender: Phone number or "Me"
                     - timestamp: Unix timestamp in milliseconds
            sender_phone: Phone number of conversation partner
            has_alias: Whether phone number has an alias in phone_lookup.txt

        Returns:
            Tuple of (should_archive, reason, confidence):
            - should_archive: True if conversation should be archived
            - reason: Human-readable explanation
            - confidence: 0.0-1.0 score indicating filter reliability

        Example:
            filter = ConversationFilter(keyword_protection)
            should_archive, reason, confidence = filter.should_archive_conversation(
                messages=[{'text': '2FA code: 123456', 'sender': '+1234567890'}],
                sender_phone='+1234567890',
                has_alias=False
            )
            # Returns: (True, "2FA/verification code pattern", 0.98)
        """
        # STEP 1: Protected-First - Check keyword protection FIRST
        if self.keyword_protection:
            is_protected, matched_keyword = self.keyword_protection.is_protected(
                messages,
                conversation_id=sender_phone  # Pass conversation ID for filename matching
            )
            if is_protected:
                logger.debug(
                    f"Conversation {sender_phone} protected by keyword: {matched_keyword}"
                )
                return False, f"Protected: matches '{matched_keyword}'", 1.0

        # STEP 2: Run filtering patterns (ordered by confidence)
        # Very Safe Patterns (0.95-0.98)
        result = self._check_2fa_verification_codes(messages)
        if result:
            return result

        result = self._check_delivery_notifications(messages)
        if result:
            return result

        result = self._check_stop_only_messages(messages)
        if result:
            return result

        result = self._check_appointment_reminders(messages)
        if result:
            return result

        result = self._check_banking_alerts(messages)
        if result:
            return result

        # Safe Patterns (0.85-0.94)
        result = self._check_political_campaigns(messages)
        if result:
            return result

        result = self._check_marketing_promotions(messages)
        if result:
            return result

        result = self._check_medical_billing(messages, sender_phone)
        if result:
            return result

        result = self._check_survey_polls(messages)
        if result:
            return result

        result = self._check_template_messages(messages)
        if result:
            return result

        # Aggressive Patterns (0.75-0.84)
        result = self._check_one_way_broadcast(messages)
        if result:
            return result

        result = self._check_short_lived_conversation(messages)
        if result:
            return result

        result = self._check_link_heavy_messages(messages)
        if result:
            return result

        result = self._check_no_alias_with_keywords(messages, has_alias)
        if result:
            return result

        result = self._check_noreply_pattern(messages, sender_phone)
        if result:
            return result

        result = self._check_voicemail_only_conversation(messages)
        if result:
            return result

        # No filter matched - keep conversation
        return False, "No filter matched", 0.0

    # -------------------------------------------------------------------------
    # Very Safe Patterns (0.95-0.98 confidence)
    # -------------------------------------------------------------------------

    def _check_2fa_verification_codes(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 1: 2FA/Verification codes (0.98 confidence)

        Matches:
        - "Your verification code is 123456"
        - "2FA code: 789012"
        - "Use code 456789 to sign in"
        """
        patterns = [
            r'\bverification code\b',
            r'\b2fa code\b',
            r'\bauth code\b',
            r'\bsecurity code\b',
            r'\bone.?time password\b',
            r'\botp\b.*\d{4,}',
            r'\bcode\s*[:\-]?\s*\d{4,}',
            r'\buse\s+code\s+\d{4,}'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "2FA/verification code pattern", 0.98

        return None

    def _check_delivery_notifications(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 2: Delivery notifications (0.97 confidence)

        Matches:
        - "Your order has been picked up"
        - "Your order was dropped off"
        - "Dasher is on the way"
        - "your Dasher provided"
        - "Package delivered"
        - "Caviar connecting you to your Dasher"
        - "I left your delivery at your door"
        - "delivered to your door"
        """
        patterns = [
            # Original patterns
            r'\border\s+(has been|was)\s+(picked up|delivered)',
            r'\bdasher\s+is\s+(on the way|nearby|arriving)',
            r'\bdelivery\s+update',
            r'\bpackage\s+(delivered|out for delivery)',
            r'\btracking\s+(number|update)',
            r'\byour\s+(doordash|ubereats|grubhub|postmates)\s+order',
            r'\byour\s+(doordash|ubereats|grubhub|postmates)\s+driver\b',

            # Dropped off patterns
            r'\border\s+(was\s+)?dropped\s+off',
            r'\bdropped\s+off.*\bdasher\b',

            # Broader Dasher patterns
            r'\byour\s+dasher\b',
            r'\bconnecting\s+you\s+to\s+your\s+dasher\b',

            # Additional delivery services
            r'\byour\s+caviar\s+(order|delivery)\b',
            r'\bcaviar\s+connecting\b',
            r'\binstacart\s+(shopper|delivery)\b',

            # NEW: Generic delivery driver messages
            r'\bleft\s+your\s+delivery\b',
            r'\bleft\s+(at|outside)\s+your\s+door\b',
            r'\bdelivered\s+to\s+your\s+door\b',
            r'\bdelivery\s+at\s+your\s+door\b',
            r'\bleft\s+(the\s+)?(package|order)\s+(at|outside)\b',
        ]

        # Also check for high message count with no replies
        user_messages = [m for m in messages if m.get("sender") == "Me"]
        total_messages = len(messages)

        # 50+ messages with 0 replies = automated delivery spam
        if total_messages >= 50 and len(user_messages) == 0:
            return True, "High volume automated delivery notifications", 0.97

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "Delivery notification pattern", 0.97

        return None

    def _check_stop_only_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 3: STOP-only messages (0.96 confidence)

        Matches:
        - Single message: "Stop"
        - Single message: "STOP 2 END"
        - Single message: "Unsubscribe"
        """
        if len(messages) == 1:
            text = messages[0].get("text", "").strip().lower()
            stop_patterns = [
                r'^stop$',
                r'^stop\s+(2|to)\s+end$',
                r'^unsubscribe$',
                r'^optout$',
                r'^cancel$'
            ]
            for pattern in stop_patterns:
                if re.match(pattern, text, re.IGNORECASE):
                    return True, "STOP-only orphan message", 0.96

        return None

    def _check_appointment_reminders(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 4: Appointment reminders (0.95 confidence)

        Matches:
        - "Reminder: Your appointment on 12/15 at 3pm"
        - "Confirm your appointment"
        """
        patterns = [
            r'\bappointment\s+reminder\b',
            r'\bconfirm your appointment\b',
            r'\bscheduled for\b',
            r'\breply\s+y\s+to\s+confirm\b',
            r'\bappointment\s+on\s+\d{1,2}[/\-]\d{1,2}'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "Appointment reminder pattern", 0.95

        return None

    def _check_banking_alerts(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 5: Banking/financial alerts (0.95 confidence)

        Matches:
        - "Your account balance is $123.45"
        - "Transaction alert: $50.00 at Starbucks"
        """
        patterns = [
            r'\baccount\s+balance\b',
            r'\btransaction\s+(alert|notification)\b',
            r'\bcharged\s+\$\d+',
            r'\bdeposit\s+(of|for)\s+\$\d+',
            r'\blow\s+balance\s+(alert|warning)\b',
            r'\bfraud\s+alert\b'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "Banking/financial alert pattern", 0.95

        return None

    # -------------------------------------------------------------------------
    # Safe Patterns (0.85-0.94 confidence)
    # -------------------------------------------------------------------------

    def _check_political_campaigns(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 6: Political campaign messages (0.92 confidence)

        Matches:
        - "HUGE 700% MATCH to stand with Kamala"
        - "Do you ENDORSE Kamala Harris?"
        - "Donate to support..."
        - "Stop to Quit" / "Stop to End"
        - "donate $5 or $10"
        - "Senate Majority"
        - "pass [politician]'s bill"
        """
        patterns = [
            # Original donate patterns
            r'\b(donate|contribute|chip in)\s+(to|now)\b',
            # NEW: Donate with dollar amounts (e.g., "donate $5", "donate $10 TODAY")
            r'\b(donate|contribute|chip in)\s+\$\d+',
            # NEW: Broader donation patterns
            r'\b(donate|contribute)\b.*\$(to|now|today)\b',

            # Matching patterns
            r'\b\d+%\s+match(ing)?\b',

            # Endorsement patterns
            r'\bendorse\s+\w+\s+(harris|trump|biden)\b',
            r'\bvote\s+for\s+\w+\b',

            # Campaign patterns
            r'\bcampaign\s+(contribution|donation)\b',
            r'\bpolitical\s+(survey|poll)\b',
            r'\bdem(ocratic)?\s+congress\b',

            # NEW: Senate/congressional patterns
            r'\bsenate\s+majority\b',
            r'\b(pass|support|sign)\s+\w+\'?s\s+(bill|act)\b',
            r'\bjon\s+tester\b',  # Known political figures

            # Stop patterns (common in political SMS)
            r'\bstop\s+to\s+(end|quit)\b',
            r'\bstop\s+2\s+(end|quit)\b',

            # NEW: Political action patterns
            r'\bruin\s+(trump|biden|harris)\b',
            r'\bstand\s+with\s+(kamala|trump|biden)\b',
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "Political campaign pattern", 0.92

        return None

    def _check_marketing_promotions(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 7: Marketing promotions (0.90 confidence)

        Matches:
        - "FLASH SALE: 50% OFF"
        - "Limited time offer"
        - "Click here to claim"
        """
        patterns = [
            r'\bflash\s+sale\b',
            r'\blimited\s+time\s+offer\b',
            r'\b\d+%\s+off\b',
            r'\bexclusive\s+deal\b',
            r'\bclaim\s+your\s+(discount|offer)\b',
            r'\bpromo\s+code\b',
            r'\bshop\s+now\b',
            r'\bfree\s+shipping\b'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "Marketing promotion pattern", 0.90

        return None

    def _check_medical_billing(
        self,
        messages: List[Dict[str, Any]],
        sender_phone: str
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 8: Medical billing (0.88 confidence)

        Matches:
        - Toll-free numbers (800, 888, 866, 877, 855)
        - "Your bill is ready"
        - "Statement available"
        """
        # Check for toll-free numbers
        if sender_phone.startswith('+1'):
            area_code = sender_phone[2:5]
            if area_code in ['800', '888', '866', '877', '855']:
                # Check for billing keywords
                billing_patterns = [
                    r'\bbill\s+is\s+(ready|available)\b',
                    r'\bstatement\s+(ready|available)\b',
                    r'\bpayment\s+due\b',
                    r'\bmedical\s+bill\b'
                ]
                for msg in messages:
                    text = msg.get("text", "").lower()
                    for pattern in billing_patterns:
                        if re.search(pattern, text, re.IGNORECASE):
                            return True, "Medical billing (toll-free + keywords)", 0.88

        return None

    def _check_survey_polls(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 9: Surveys and polls (0.87 confidence)

        Matches:
        - "Live Survey: Do you..."
        - "Take our quick poll"
        """
        patterns = [
            r'\blive\s+survey\b',
            r'\btake\s+our\s+(survey|poll)\b',
            r'\bquick\s+(poll|survey)\b',
            r'\brate\s+your\s+experience\b',
            r'\b\d+\s+question\s+survey\b',
            r'\bhow\s+would\s+you\s+rate\b'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "Survey/poll pattern", 0.87

        return None

    def _check_template_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 10: Template/duplicate messages (0.85 confidence)

        Matches:
        - Multiple identical messages
        - All messages from same sender (no user replies)
        """
        if len(messages) < 3:
            return None

        # Check for exact duplicates
        message_texts = [m.get("text", "") for m in messages]
        unique_texts = set(message_texts)

        # If >50% messages are identical, likely template
        if len(unique_texts) < len(message_texts) * 0.5:
            return True, "Template/duplicate message pattern", 0.85

        return None

    # -------------------------------------------------------------------------
    # Aggressive Patterns (0.75-0.84 confidence)
    # -------------------------------------------------------------------------

    def _check_one_way_broadcast(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 11: One-way broadcast (0.82 confidence)

        Matches:
        - All messages from sender, no user replies
        - 2+ messages (lowered from 3+ to catch more spam)
        """
        if len(messages) < 2:
            return None

        user_messages = [m for m in messages if m.get("sender") == "Me"]
        if len(user_messages) == 0:
            return True, "One-way broadcast (no user replies)", 0.82

        return None

    def _check_short_lived_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 12: Short-lived conversation (0.80 confidence)

        Matches:
        - All messages within 1 hour
        - Only 1-2 messages total
        """
        if len(messages) > 2:
            return None

        if len(messages) == 0:
            return None

        timestamps = [m.get("timestamp", 0) for m in messages]
        time_span = max(timestamps) - min(timestamps)

        # 1 hour = 3600000 milliseconds
        if time_span <= 3600000:
            return True, "Short-lived conversation (<1 hour)", 0.80

        return None

    def _check_link_heavy_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 13: Link-heavy messages (0.78 confidence)

        Matches:
        - >75% of messages contain URLs
        """
        if len(messages) < 2:
            return None

        url_pattern = r'https?://\S+'
        messages_with_links = 0

        for msg in messages:
            text = msg.get("text", "")
            if re.search(url_pattern, text):
                messages_with_links += 1

        link_percentage = messages_with_links / len(messages)
        if link_percentage > 0.75:
            return True, "Link-heavy messages (>75% contain URLs)", 0.78

        return None

    def _check_no_alias_with_keywords(
        self,
        messages: List[Dict[str, Any]],
        has_alias: bool
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 14: No alias + commercial keywords (0.76 confidence)

        Matches:
        - Phone number has no alias
        - Messages contain commercial keywords
        """
        if has_alias:
            return None

        commercial_keywords = [
            'unsubscribe', 'opt out', 'stop to end', 'msg&data rates',
            'customer service', 'support center', 'help desk',
            'automated message', 'do not reply'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for keyword in commercial_keywords:
                if keyword in text:
                    return True, f"No alias + commercial keyword: '{keyword}'", 0.76

        return None

    def _check_noreply_pattern(
        self,
        messages: List[Dict[str, Any]],
        sender_phone: str
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 15: No-reply pattern (0.75 confidence)

        Matches:
        - Messages contain "do not reply"
        - Messages contain "noreply"
        """
        noreply_patterns = [
            r'\bdo\s+not\s+reply\b',
            r'\bno\s+reply\b',
            r'\bnoreply\b',
            r'\bauto(mated)?\s+(message|notification)\b'
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            for pattern in noreply_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True, "No-reply/automated message pattern", 0.75

        return None

    def _check_voicemail_only_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Tuple[bool, str, float]]:
        """
        Pattern 16: Voicemail-only conversation (0.77 confidence)

        Matches:
        - Single voicemail message with no replies
        - Unsolicited business contacts
        - Financial institution cold contacts

        Patterns:
        - "🎙️ Voicemail from" (single message)
        - "would love to set up time"
        - "Private Client advisor", "Private Banker"
        - Financial institution names
        """
        # Must be exactly 1 message
        if len(messages) != 1:
            return None

        msg = messages[0]
        text = msg.get("text", "").lower()

        # Must be a voicemail
        if "🎙️ voicemail from" not in text.lower():
            return None

        # Check for unsolicited business contact patterns
        business_patterns = [
            # Financial services cold contacts
            r'\bprivate\s+(client|banker)\s+advisor\b',
            r'\bwould\s+love\s+to\s+set\s+up\s+(some\s+)?time\b',
            r'\bjust\s+wanted\s+to\s+reach\s+out\b',
            r'\bintroduce\s+myself\b',

            # Financial institutions
            r'\bjpmorgan\s+chase\b',
            r'\bwells\s+fargo\b',
            r'\bbank\s+of\s+america\b',
            r'\bcitibank\b',
            r'\bgoldman\s+sachs\b',
            r'\bmorgan\s+stanley\b',

            # Business development
            r'\breaching\s+out\s+to\s+(discuss|introduce)\b',
            r'\bfollow\s+up\s+on\s+your\s+(account|inquiry)\b',
            r'\brelationship\s+manager\b',
            r'\baccount\s+manager\b',
        ]

        for pattern in business_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, "Voicemail-only unsolicited business contact", 0.77

        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get filter statistics.

        Returns:
            Dictionary with filter stats
        """
        return {
            "total_patterns": 16,
            "very_safe_patterns": 5,
            "safe_patterns": 5,
            "aggressive_patterns": 6,
            "keyword_protection_enabled": self.keyword_protection is not None
        }
