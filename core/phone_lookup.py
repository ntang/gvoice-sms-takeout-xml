"""
Phone Lookup Manager for SMS/MMS processing.

This module handles phone number to alias mappings with user interaction
during SMS/MMS conversion.
"""

import logging
import re
import threading
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PhoneLookupManager:
    """Manages phone number to alias mappings with user interaction."""

    def __init__(self, lookup_file: Path, enable_prompts: bool = True):
        # Validate parameters
        if not isinstance(lookup_file, Path):
            raise TypeError(
                f"lookup_file must be a Path, got {type(lookup_file).__name__}"
            )
        if not isinstance(enable_prompts, bool):
            raise TypeError(
                f"enable_prompts must be a boolean, got {type(enable_prompts).__name__}"
            )

        self.lookup_file = lookup_file
        self.enable_prompts = enable_prompts
        self.phone_aliases = {}  # Maps phone numbers to aliases

        # Thread safety: Add lock for file operations
        self._file_lock = threading.Lock()

        self.load_aliases()

        # Register cleanup handler to save aliases on exit
        import atexit

        atexit.register(self.force_save_aliases)

    def load_aliases(self):
        """Load existing phone number aliases from file."""
        with self._file_lock:
            try:
                if self.lookup_file.exists():
                    with open(self.lookup_file, "r", encoding="utf8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                try:
                                    phone, alias = line.split("|", 1)
                                    phone = phone.strip()
                                    alias = alias.strip()

                                    # Check for exclusion patterns
                                    if alias.startswith("EXCLUDE:"):
                                        # This number should be excluded from processing
                                        self.phone_aliases[
                                            phone
                                        ] = f"EXCLUDE:{alias[8:]}"
                                        logger.debug(
                                            f"Loaded exclusion for {phone}: {alias}"
                                        )
                                    else:
                                        # Normal alias
                                        self.phone_aliases[phone] = alias

                                except ValueError:
                                    # Skip malformed lines
                                    continue
                    logger.info(
                        f"Loaded {len(self.phone_aliases)} phone number aliases from {self.lookup_file}"
                    )
                    logger.debug(f"Loaded aliases: {self.phone_aliases}")
                else:
                    # Create the file with a header
                    try:
                        self.lookup_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(self.lookup_file, "w", encoding="utf8") as f:
                            f.write("# Phone number lookup file\n")
                            f.write("# Format: phone_number|alias\n")
                            f.write("# Lines starting with # are comments\n")
                            f.write(
                                "# To exclude a number, use: phone_number|EXCLUDE:reason\n"
                            )
                            f.write("# Example: +1234567890|EXCLUDE:spam\n")
                        logger.info(f"Created new phone lookup file: {self.lookup_file}")
                    except Exception as create_error:
                        logger.warning(f"Could not create phone lookup file: {create_error}")
                        # In test environments, this might be expected
            except Exception as e:
                logger.error(f"Failed to load phone aliases: {e}")
                # In test environments, this might be expected, so don't raise

    def save_aliases(self):
        """Save phone number aliases to file."""
        with self._file_lock:
            try:
                # Ensure the parent directory exists
                self.lookup_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.lookup_file, "w", encoding="utf8") as f:
                    f.write("# Phone number lookup file\n")
                    f.write("# Format: phone_number|alias\n")
                    f.write("# Lines starting with # are comments\n")
                    for phone, alias in sorted(self.phone_aliases.items()):
                        f.write(f"{phone}|{alias}\n")
                logger.info(
                    f"Saved {len(self.phone_aliases)} phone number aliases to {self.lookup_file}"
                )
            except Exception as e:
                logger.error(f"Failed to save phone aliases: {e}")
                # In test environments, this might be expected, so don't raise
                # Just log the error and continue

    def save_aliases_batched(self, batch_every: int = 100):
        """Save aliases only every N new entries to reduce disk IO."""
        if not hasattr(self, "_unsaved_count"):
            self._unsaved_count = 0
        self._unsaved_count += 1
        if self._unsaved_count >= batch_every:
            self.save_aliases()
            self._unsaved_count = 0

    def force_save_aliases(self):
        """Force save all aliases immediately to disk."""
        try:
            self.save_aliases()
            logger.info(
                f"Force saved all {len(self.phone_aliases)} aliases to {self.lookup_file}"
            )
        except Exception as e:
            logger.warning(f"Could not force save aliases: {e}")
            # In test environments, this might be expected

    def get_unsaved_count(self) -> int:
        """Get the number of unsaved aliases."""
        if not hasattr(self, "_unsaved_count"):
            self._unsaved_count = 0
        return self._unsaved_count

    def sanitize_alias(self, alias: str) -> str:
        """Sanitize alias by removing special characters and replacing spaces with underscores."""
        # Remove special characters except alphanumeric, spaces, and hyphens
        sanitized = re.sub(r"[^\w\s\-]", "", alias)
        # Replace spaces and hyphens with underscores
        sanitized = re.sub(r"[\s\-]+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown"
        return sanitized

    def extract_alias_from_html(
        self, soup: BeautifulSoup, phone_number: str
    ) -> Optional[str]:
        """
        Automatically extract phone alias from HTML content when prompts are disabled.

        Args:
            soup: BeautifulSoup object of the HTML file
            phone_number: Phone number to find alias for

        Returns:
            Optional[str]: Extracted alias or None if not found
        """
        try:
            # Define generic phrases that should not be used as aliases
            generic_phrases = {
                "me",
                "unknown",
                "placed call to",
                "received call from",
                "missed call from",
                "call placed to",
                "call received from",
                "call missed from",
                "voicemail from",
                "voicemail received from",
                "text message from",
                "message from",
            }

            # Look for vCard entries with the phone number
            # Pattern: <a class="tel" href="tel:+1234567890"><span class="fn">Name</span></a>
            tel_links = soup.select('a[class*="tel"][href^="tel:"]')
            for link in tel_links:
                href = link.get("href", "")
                if href.startswith("tel:"):
                    link_phone = href.split(":", 1)[-1]
                    if link_phone == phone_number:
                        # First try to find the name in the fn class
                        fn_element = link.find(["span", "abbr"], class_="fn")
                        if fn_element:
                            name = fn_element.get_text(strip=True)
                            if name and name.lower() not in generic_phrases:
                                return self.sanitize_alias(name)

                        # If no fn class, try to get the name directly from the tel link text
                        # This handles cases like: <a class="tel" href="tel:+1234567890">Name</a>
                        link_text = link.get_text(strip=True)
                        if link_text and link_text.lower() not in generic_phrases:
                            return self.sanitize_alias(link_text)

            # Look for other patterns where phone numbers and names are associated
            # Pattern: <cite class="sender vcard"><a class="tel" href="tel:+1234567890">Name</a></cite>
            cite_elements = soup.find_all("cite", class_=lambda x: x and "sender" in x)
            for cite in cite_elements:
                tel_link = cite.find("a", class_="tel", href=True)
                if tel_link:
                    href = tel_link.get("href", "")
                    if href.startswith("tel:"):
                        link_phone = href.split(":", 1)[-1]
                        if link_phone == phone_number:
                            name = tel_link.get_text(strip=True)
                            if name and name.lower() not in generic_phrases:
                                return self.sanitize_alias(name)

            # Look for general name elements near phone numbers
            # Pattern: <span class="fn">Name</span> or similar
            fn_elements = soup.select('span[class*="fn"], abbr[class*="fn"]')
            for fn in fn_elements:
                name = fn.get_text(strip=True)
                if name and name.lower() not in generic_phrases:
                    # Check if this name element is near a phone number
                    # Look for tel links in the same container or nearby
                    container = fn.find_parent(["div", "span", "cite"])
                    if container:
                        tel_links = container.select('a[class*="tel"][href^="tel:"]')
                        for tel_link in tel_links:
                            href = tel_link.get("href", "")
                            if href.startswith("tel:"):
                                link_phone = href.split(":", 1)[-1]
                                if link_phone == phone_number:
                                    return self.sanitize_alias(name)

            return None

        except Exception as e:
            logger.debug(f"Failed to extract alias from HTML for {phone_number}: {e}")
            return None

    def get_alias(self, phone_number: str, soup: Optional[BeautifulSoup] = None) -> str:
        """Get alias for a phone number, prompting user if not found and prompts are enabled."""
        logger.debug(f"Looking up alias for phone number: '{phone_number}'")
        logger.debug(f"Available aliases: {list(self.phone_aliases.keys())}")

        if phone_number in self.phone_aliases:
            logger.debug(
                f"Found existing alias for {phone_number}: {self.phone_aliases[phone_number]}"
            )
            return self.phone_aliases[phone_number]

        if not self.enable_prompts:
            # Try to automatically extract alias from HTML if provided
            if soup:
                extracted_alias = self.extract_alias_from_html(soup, phone_number)
                if extracted_alias:
                    # Store the automatically extracted alias
                    self.phone_aliases[phone_number] = extracted_alias
                    self.save_aliases_batched()
                    logger.info(
                        f"Automatically extracted alias '{extracted_alias}' for {phone_number}"
                    )
                    return extracted_alias

            return phone_number

        # Prompt user for alias
        try:
            print(f"\nNew phone number found: {phone_number}")
            print(
                "Please provide a name/alias for this number (or press Enter to use the number):"
            )
            alias = input("Alias: ").strip()

            if alias:
                # Sanitize the alias
                sanitized_alias = self.sanitize_alias(alias)
                if sanitized_alias != alias:
                    print(f"Alias sanitized to: {sanitized_alias}")

                # Store the mapping
                self.phone_aliases[phone_number] = sanitized_alias

                # CRITICAL: Save immediately to disk to prevent data loss
                # Don't use batched saving for user-specified aliases
                self.save_aliases()
                logger.info(
                    f"Immediately saved alias '{sanitized_alias}' for {phone_number} to {self.lookup_file}"
                )

                return sanitized_alias
            else:
                # User chose to use the phone number
                return phone_number

        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+D or Ctrl+C gracefully
            print("\nUsing phone number as alias.")
            return phone_number
        except Exception as e:
            logger.error(f"Failed to get alias for {phone_number}: {e}")
            return phone_number

    def get_all_aliases(self) -> Dict[str, str]:
        """Get all phone number to alias mappings."""
        return self.phone_aliases.copy()

    def add_alias(self, phone_number: str, alias: str):
        """Manually add a phone number to alias mapping."""
        sanitized_alias = self.sanitize_alias(alias)
        self.phone_aliases[phone_number] = sanitized_alias

        # CRITICAL: Save immediately to disk to prevent data loss
        self.save_aliases()
        logger.info(
            f"Immediately saved alias '{sanitized_alias}' for phone number {phone_number} to {self.lookup_file}"
        )

    def is_excluded(self, phone_number: str) -> bool:
        """Check if a phone number is excluded from processing."""
        if phone_number in self.phone_aliases:
            alias = self.phone_aliases[phone_number]
            return alias.startswith("EXCLUDE:")
        return False

    def get_exclusion_reason(self, phone_number: str) -> Optional[str]:
        """Get the reason why a phone number is excluded, if any."""
        if phone_number in self.phone_aliases:
            alias = self.phone_aliases[phone_number]
            if alias.startswith("EXCLUDE:"):
                return alias[8:]  # Remove "EXCLUDE:" prefix
        return None

    def has_alias(self, phone_number: str) -> bool:
        """Check if a phone number has a non-exclusion alias."""
        if phone_number in self.phone_aliases:
            alias = self.phone_aliases[phone_number]
            return not alias.startswith("EXCLUDE:")
        return False

    def add_exclusion(self, phone_number: str, reason: str = "excluded"):
        """Add a phone number to the exclusion list."""
        exclusion_alias = f"EXCLUDE:{reason}"
        self.phone_aliases[phone_number] = exclusion_alias

        # CRITICAL: Save immediately to disk to prevent data loss
        self.save_aliases()
        logger.info(
            f"Immediately saved exclusion for {phone_number}: {reason} to {self.lookup_file}"
        )
