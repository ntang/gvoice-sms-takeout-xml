"""Template package for Google Voice SMS Takeout HTML Converter."""

from .loader import (
    TemplateLoader,
    get_template_loader,
    format_index_template,
    format_conversation_template,
)

# XML template imports removed - only HTML output supported

__all__ = [
    "TemplateLoader",
    "get_template_loader",
    "format_index_template",
    "format_conversation_template",
]
