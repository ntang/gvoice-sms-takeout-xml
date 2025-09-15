"""Template package for Google Voice SMS Takeout XML Converter."""

from .loader import (
    TemplateLoader,
    get_template_loader,
    format_index_template,
    format_conversation_template,
)
from .config import (
    SMS_XML_TEMPLATE,
    MMS_XML_TEMPLATE,
    TEXT_PART_TEMPLATE,
    PARTICIPANT_TEMPLATE,
    IMAGE_PART_TEMPLATE,
    VCARD_PART_TEMPLATE,
    CALL_XML_TEMPLATE,
    VOICEMAIL_XML_TEMPLATE,
)

__all__ = [
    "TemplateLoader",
    "get_template_loader",
    "format_index_template",
    "format_conversation_template",
    "SMS_XML_TEMPLATE",
    "MMS_XML_TEMPLATE",
    "TEXT_PART_TEMPLATE",
    "PARTICIPANT_TEMPLATE",
    "IMAGE_PART_TEMPLATE",
    "VCARD_PART_TEMPLATE",
    "CALL_XML_TEMPLATE",
    "VOICEMAIL_XML_TEMPLATE",
]
