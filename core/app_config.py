"""
Configuration module for Google Voice SMS Takeout XML Converter.

This module centralizes all configuration constants used throughout the application.
"""

# ====================================================================
# SUPPORTED FILE TYPES
# ====================================================================

SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif"}
SUPPORTED_VCARD_TYPES = {".vcf"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_TYPES | SUPPORTED_VCARD_TYPES

# ====================================================================
# MMS MESSAGE TYPE CONSTANTS
# ====================================================================

MMS_TYPE_SENT = 128
MMS_TYPE_RECEIVED = 132

# ====================================================================
# MESSAGE BOX CONSTANTS
# ====================================================================

MESSAGE_BOX_SENT = 2
MESSAGE_BOX_RECEIVED = 1

# ====================================================================
# PARTICIPANT TYPE CODES FOR MMS
# ====================================================================

PARTICIPANT_TYPE_SENDER = 137
PARTICIPANT_TYPE_RECEIVED = 151

# ====================================================================
# HASH-BASED FALLBACK CONFIGURATION
# ====================================================================

UNKNOWN_NUMBER_PREFIX = "UN_"
UNKNOWN_NUMBER_HASH_LENGTH = 22  # Base64 encoded MD5 length
UNKNOWN_NUMBER_PATTERN = f"^{UNKNOWN_NUMBER_PREFIX}[a-f0-9_-]{{{UNKNOWN_NUMBER_HASH_LENGTH}}}$"

# ====================================================================
# DEFAULT VALUES AND THRESHOLDS
# ====================================================================

DEFAULT_FALLBACK_TIME = 1000  # milliseconds
MIN_PHONE_NUMBER_LENGTH = 7
FILENAME_TRUNCATE_LENGTH = 50

# ====================================================================
# MMS PLACEHOLDER MESSAGES
# ====================================================================

MMS_PLACEHOLDER_MESSAGES = {"MMS Sent", "MMS Received"}

# ====================================================================
# HTML PARSING CONSTANTS
# ====================================================================

HTML_PARSER = "html.parser"
GROUP_CONVERSATION_MARKER = "Group Conversation"

# ====================================================================
# ERROR MESSAGES
# ====================================================================

ERROR_NO_MESSAGES = "No messages found in HTML file"
ERROR_NO_PARTICIPANTS = "Could not find participant phone number"
ERROR_NO_SENDER = "Unable to determine sender in MMS with multiple participants"

# ====================================================================
# CONFIGURATION EXPORT
# ====================================================================

DEFAULT_CONFIG = {
    "SUPPORTED_IMAGE_TYPES": SUPPORTED_IMAGE_TYPES,
    "SUPPORTED_VCARD_TYPES": SUPPORTED_VCARD_TYPES,
    "MMS_TYPE_SENT": MMS_TYPE_SENT,
    "MMS_TYPE_RECEIVED": MMS_TYPE_RECEIVED,
    "MESSAGE_BOX_SENT": MESSAGE_BOX_SENT,
    "MESSAGE_BOX_RECEIVED": MESSAGE_BOX_RECEIVED,
    "PARTICIPANT_TYPE_SENDER": PARTICIPANT_TYPE_SENDER,
    "PARTICIPANT_TYPE_RECEIVED": PARTICIPANT_TYPE_RECEIVED,
    "UNKNOWN_NUMBER_PREFIX": UNKNOWN_NUMBER_PREFIX,
    "UNKNOWN_NUMBER_HASH_LENGTH": UNKNOWN_NUMBER_HASH_LENGTH,
    "UNKNOWN_NUMBER_PATTERN": UNKNOWN_NUMBER_PATTERN,
}
