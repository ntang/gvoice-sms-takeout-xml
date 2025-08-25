"""Template loader utility for Google Voice SMS Takeout XML Converter."""

from pathlib import Path
from typing import Dict, Any


class TemplateLoader:
    """Loads and formats HTML and XML templates."""

    def __init__(self, templates_dir: Path = None):
        """Initialize template loader.

        Args:
            templates_dir: Directory containing template files
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent
        self.templates_dir = templates_dir
        self._templates = {}
        self._load_templates()

    def _load_templates(self):
        """Load all template files into memory."""
        template_files = {
            "index": "index.html",
            "conversation": "conversation.html",
        }

        for name, filename in template_files.items():
            template_path = self.templates_dir / filename
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    self._templates[name] = f.read()

    def get_template(self, name: str) -> str:
        """Get a template by name.

        Args:
            name: Template name (e.g., 'index', 'conversation')

        Returns:
            Template content as string

        Raises:
            KeyError: If template not found
        """
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found")
        return self._templates[name]

    def format_template(self, name: str, **kwargs) -> str:
        """Format a template with the given parameters.

        Args:
            name: Template name
            **kwargs: Parameters to format into template

        Returns:
            Formatted template string
        """
        template = self.get_template(name)
        return template.format(**kwargs)

    def format_index_template(self, **kwargs) -> str:
        """Format the index template with conversation data.

        Args:
            **kwargs: Must include elapsed_time, output_format, total_conversations,
                     num_sms, num_calls, num_voicemails, num_img, num_vcf,
                     total_messages, conversation_rows, timestamp

        Returns:
            Formatted index HTML
        """
        return self.format_template("index", **kwargs)

    def format_conversation_template(self, **kwargs) -> str:
        """Format the conversation template with message data.

        Args:
            **kwargs: Must include conversation_id, total_messages, message_rows

        Returns:
            Formatted conversation HTML
        """
        return self.format_template("conversation", **kwargs)


# Global template loader instance
_template_loader = None


def get_template_loader() -> TemplateLoader:
    """Get the global template loader instance."""
    global _template_loader
    if _template_loader is None:
        _template_loader = TemplateLoader()
    return _template_loader


def format_index_template(**kwargs) -> str:
    """Format the index template using the global loader."""
    return get_template_loader().format_index_template(**kwargs)


def format_conversation_template(**kwargs) -> str:
    """Format the conversation template using the global loader."""
    return get_template_loader().format_conversation_template(**kwargs)
