"""
Conversation Manager for SMS/MMS processing.

This module handles the creation and management of conversation files
for different senders/groups during SMS/MMS conversion.
"""

import logging
import threading
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

# Template imports removed - not used in this module

logger = logging.getLogger(__name__)


class StringBuilder:
    """Efficient string builder for concatenating multiple strings."""

    def __init__(self, initial_capacity=1024):
        self.parts = []
        self.length = 0
        self.initial_capacity = initial_capacity

    def append(self, text: str):
        """Append text to the builder."""
        if text:
            self.parts.append(text)
            self.length += len(text)

            # Prevent excessive memory usage by limiting parts list size
            if len(self.parts) > 1000:  # Arbitrary limit to prevent memory leaks
                # Combine parts into larger chunks to reduce list size
                combined = "".join(self.parts[:500])
                self.parts = [combined] + self.parts[500:]
                self.length = sum(len(part) for part in self.parts)

    def append_line(self, text: str = ""):
        """Append text with a newline."""
        self.append(text + "\n")

    def build(self) -> str:
        """Build the final string."""
        if not self.parts:
            return ""
        if len(self.parts) == 1:
            return self.parts[0]
        return "".join(self.parts)

    def clear(self):
        """Clear the builder."""
        self.parts.clear()
        self.length = 0

    def __len__(self):
        return self.length

    def cleanup(self):
        """Clean up memory by combining parts and reducing list size."""
        if len(self.parts) > 100:
            combined = "".join(self.parts)
            self.parts = [combined]
            self.length = len(combined)

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.cleanup()


class ConversationManager:
    """Manages conversation files for different senders/groups."""

    def __init__(
        self,
        output_dir: Path,
        buffer_size: int = 8192,
        batch_size: int = 1000,
        large_dataset: bool = False,
        output_format: str = "xml",
    ):
        # Validate parameters
        if not isinstance(output_dir, Path):
            raise TypeError(
                f"output_dir must be a Path, got {type(output_dir).__name__}"
            )
        if not isinstance(buffer_size, int) or buffer_size <= 0:
            raise ValueError(
                f"buffer_size must be a positive integer, got {buffer_size}"
            )
        if not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError(f"batch_size must be a positive integer, got {batch_size}")
        if not isinstance(output_format, str) or output_format not in ["xml", "html"]:
            raise ValueError(
                f"output_format must be 'xml' or 'html', got {output_format}"
            )

        self.output_dir = output_dir
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_files = (
            {}
        )  # Maps conversation_id to file handle and message count
        self.conversation_stats = {}  # Maps conversation_id to statistics
        self.write_buffer_size = (
            buffer_size  # Configurable buffer size for efficient I/O
        )
        self.message_buffer = {}  # Buffer messages before writing to reduce I/O

        # Thread-safety for concurrent writes and file creation
        self._lock = threading.RLock()

        # Pre-allocate common data structures for better performance
        self._empty_list = []
        self._empty_dict = {}

        # Memory-efficient processing for large datasets
        self._batch_size = batch_size if batch_size > 0 else 1000
        self._memory_threshold = (
            100000 if large_dataset else 50000
        )  # Adjust threshold based on dataset size

        self.output_format = output_format

    def get_conversation_id(
        self, participants: List[str], is_group: bool = False, phone_lookup_manager=None
    ) -> str:
        """Generate a unique conversation ID for participants."""
        if is_group:
            # For group conversations, create a filename with concatenated aliases
            if not participants:
                return "group_unknown"

            # Get aliases for all participants
            participant_aliases = []
            for phone in participants:
                # Use the phone lookup manager if available, otherwise use phone number
                if phone_lookup_manager:
                    alias = phone_lookup_manager.get_alias(phone, None)
                else:
                    alias = phone
                participant_aliases.append(alias)

            # Remove duplicates while preserving order
            unique_aliases = []
            seen = set()
            for alias in participant_aliases:
                if alias not in seen:
                    unique_aliases.append(alias)
                    seen.add(alias)

            if len(unique_aliases) <= 6:
                # For 6 or fewer participants, use full aliases
                conversation_id = "_".join(unique_aliases)
            else:
                # For more than 6 participants, truncate aliases and add stable hash
                # Take first 5 aliases and truncate them before first underscore
                truncated_aliases = []
                for alias in unique_aliases[:5]:
                    # Truncate before first underscore if it exists
                    truncated = alias.split("_")[0] if "_" in alias else alias
                    truncated_aliases.append(truncated)

                # Create stable hash for remaining participants
                remaining_participants = unique_aliases[5:]
                stable = hashlib.sha1(
                    "_".join(remaining_participants).encode("utf-8")
                ).hexdigest()[:6]

                conversation_id = (
                    "_".join(truncated_aliases)
                    + f"_and_{len(remaining_participants)}_more_{stable}"
                )

            # Ensure the filename is not too long (max ~100 characters)
            if len(conversation_id) > 100:
                # Fall back to stable hash-based naming if too long
                participants_str = "_".join(unique_aliases)
                stable = hashlib.sha1(participants_str.encode("utf-8")).hexdigest()[:8]
                conversation_id = f"group_{stable}"

            return conversation_id
        else:
            # For individual conversations, use the alias of the first participant
            if participants:
                phone_number = participants[0]
                # Validate that the phone number is valid
                try:
                    from utils import is_valid_phone_number

                    if not is_valid_phone_number(phone_number):
                        return "unknown"
                except (AttributeError, NameError, ImportError):
                    pass

                # Get alias for the phone number
                try:
                    from sms import PHONE_LOOKUP_MANAGER

                    if PHONE_LOOKUP_MANAGER:
                        alias = PHONE_LOOKUP_MANAGER.get_alias(phone_number, None)
                    else:
                        alias = phone_number
                except (AttributeError, NameError, ImportError):
                    alias = phone_number
                return alias
            else:
                return "unknown"

    def get_conversation_filename(self, conversation_id: str) -> Path:
        """Get the filename for a conversation."""
        return self.output_dir / f"{conversation_id}.{self.output_format}"

    def write_message(self, conversation_id: str, message_content: str, timestamp: int):
        """Write a message to the conversation file with optimized buffering."""
        with self._lock:
            if conversation_id not in self.conversation_files:
                # Create new conversation file with optimized buffer size
                filename = self.get_conversation_filename(conversation_id)
                file_handle = open(
                    filename, "w", encoding="utf-8", buffering=self.write_buffer_size
                )

                self.conversation_files[conversation_id] = {
                    "file": file_handle,
                    "messages": [],
                    "buffer_size": 0,
                    "max_buffer_size": self.write_buffer_size
                    * 2,  # Allow buffer to grow up to 2x
                }

                # Initialize conversation statistics
                self.conversation_stats[conversation_id] = {
                    "num_sms": 0,
                    "num_img": 0,
                    "num_vcf": 0,
                    "num_calls": 0,
                    "num_voicemails": 0,
                }

            file_info = self.conversation_files[conversation_id]

            # Add message to buffer
            file_info["messages"].append((timestamp, message_content))
            file_info["buffer_size"] += len(message_content)

            # Flush buffer if it gets too large
            if file_info["buffer_size"] > file_info["max_buffer_size"]:
                file_info["file"].flush()
                file_info["buffer_size"] = 0

    def write_message_with_content(
        self,
        conversation_id: str,
        message_text: str,
        attachments: list,
        timestamp: int,
        sender: Optional[str] = None,
    ):
        """Write a message with pre-extracted text and attachment information for HTML output."""
        with self._lock:
            if conversation_id not in self.conversation_files:
                # Create new conversation file with optimized buffer size
                filename = self.get_conversation_filename(conversation_id)
                file_handle = open(
                    filename, "w", encoding="utf-8", buffering=self.write_buffer_size
                )

                self.conversation_files[conversation_id] = {
                    "file": file_handle,
                    "messages": [],
                    "buffer_size": 0,
                    "max_buffer_size": self.write_buffer_size
                    * 2,  # Allow buffer to grow up to 2x
                }

                # Initialize conversation statistics
                self.conversation_stats[conversation_id] = {
                    "num_sms": 0,
                    "num_img": 0,
                    "num_vcf": 0,
                    "num_calls": 0,
                    "num_voicemails": 0,
                }

            file_info = self.conversation_files[conversation_id]

            # Store message with pre-extracted content for HTML output
            message_data = {
                "text": message_text,
                "attachments": attachments,
                "sender": sender or "-",
                "raw_content": None,  # Not needed for HTML output
            }
            file_info["messages"].append((timestamp, message_data))
            file_info["buffer_size"] += len(message_text)

            # Flush buffer if it gets too large
            if file_info["buffer_size"] > file_info["max_buffer_size"]:
                file_info["file"].flush()
                file_info["buffer_size"] = 0

    def finalize_conversation_files(self):
        """Finalize all conversation files by writing headers and closing tags."""
        with self._lock:
            for conversation_id, file_info in self.conversation_files.items():
                try:
                    # Sort messages by timestamp (using tuple unpacking for better performance)
                    sorted_messages = sorted(file_info["messages"], key=lambda x: x[0])

                    if self.output_format == "xml":
                        self._finalize_xml_file(
                            file_info, sorted_messages, conversation_id
                        )
                    elif self.output_format == "html":
                        self._finalize_html_file(
                            file_info, sorted_messages, conversation_id
                        )
                    else:
                        logger.error(f"Unknown output format: {self.output_format}")
                        continue

                except Exception as e:
                    logger.error(
                        f"Failed to finalize conversation file {conversation_id}: {e}"
                    )
                    if "file" in file_info:
                        file_info["file"].close()

            # Clear the conversation files dictionary
            self.conversation_files.clear()

    def generate_index_html(self, stats: Dict[str, int], elapsed_time: float):
        """Generate an index.html file with summary stats and conversation file links."""
        try:
            # Get all conversation files in the output directory
            conversation_files = []
            for file_path in self.output_dir.glob(f"*.{self.output_format}"):
                if file_path.name != "index.html":  # Exclude index.html itself
                    conversation_files.append(file_path)

            # Sort files by name for consistent ordering
            conversation_files.sort(key=lambda x: x.name)
            
            # In test mode, limit the number of conversation files processed
            # Check if we're in test mode by looking for a global variable or environment
            test_mode = False
            test_limit = 100
            
            # Try to get test mode from globals (set by sms.py)
            import sys
            if 'TEST_MODE' in globals():
                test_mode = globals()['TEST_MODE']
                test_limit = globals().get('TEST_LIMIT', 100)
            elif hasattr(sys.modules.get('__main__', None), 'TEST_MODE'):
                test_mode = sys.modules['__main__'].TEST_MODE
                test_limit = sys.modules['__main__'].TEST_LIMIT
            
            if test_mode and len(conversation_files) > test_limit:
                logger.info(f"🧪 TEST MODE: Limiting index generation to first {test_limit} conversation files out of {len(conversation_files)} total")
                conversation_files = conversation_files[:test_limit]

            # Build conversation table rows
            # conversation_rows variable removed - not used

            # Build HTML header
            builder = StringBuilder()
            builder.append_line("<!DOCTYPE html>")
            builder.append_line("<html lang='en'>")
            builder.append_line("<head>")
            builder.append_line("    <meta charset='UTF-8'>")
            builder.append_line(
                "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            )
            builder.append_line("    <title>Google Voice Conversations Index</title>")
            builder.append_line("    <style>")
            builder.append_line(
                "        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }"
            )
            builder.append_line(
                "        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }"
            )
            builder.append_line(
                "        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: center; }"
            )
            builder.append_line(
                "        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }"
            )
            builder.append_line(
                "        .stat-card { background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #667eea; }"
            )
            builder.append_line(
                "        .stat-number { font-size: 2em; font-weight: bold; color: #667eea; margin-bottom: 5px; }"
            )
            builder.append_line(
                "        .stat-label { color: #666; font-size: 0.9em; }"
            )
            builder.append_line(
                "        .conversations-table { width: 100%; border-collapse: collapse; margin-top: 20px; }"
            )
            builder.append_line(
                "        .conversations-table th, .conversations-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }"
            )
            builder.append_line(
                "        .conversations-table th { background-color: #667eea; color: white; font-weight: bold; }"
            )
            builder.append_line(
                "        .conversations-table tr:hover { background-color: #f8f9fa; }"
            )
            builder.append_line(
                "        .file-link { color: #667eea; text-decoration: none; font-weight: bold; }"
            )
            builder.append_line(
                "        .file-link:hover { text-decoration: underline; }"
            )
            builder.append_line(
                "        .file-stats { font-size: 0.9em; color: #666; }"
            )
            builder.append_line(
                "        .footer { margin-top: 30px; padding: 20px; text-align: center; color: #666; border-top: 1px solid #eee; }"
            )
            builder.append_line(
                "        .processing-info { background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745; }"
            )
            builder.append_line("    </style>")
            builder.append_line("</head>")
            builder.append_line("<body>")
            builder.append_line("    <div class='container'>")

            # Build header section
            builder.append_line("        <div class='header'>")
            builder.append_line("            <h1>📱 Google Voice Conversations</h1>")
            builder.append_line(
                "            <p>Complete overview of all processed conversations</p>"
            )
            builder.append_line("        </div>")

            # Build processing info section
            builder.append_line("        <div class='processing-info'>")
            builder.append_line(
                f"            <strong>Processing completed in {elapsed_time:.2f} seconds</strong>"
            )
            builder.append_line(
                f"            <br>Output format: {self.output_format.upper()}"
            )
            builder.append_line(
                f"            <br>Total conversations: {len(conversation_files)}"
            )
            builder.append_line("        </div>")

            # Build summary stats section
            builder.append_line("        <div class='stats-grid'>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{stats.get('num_sms', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>SMS Messages</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{stats.get('num_calls', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>Call Logs</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{stats.get('num_voicemails', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>Voicemails</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{stats.get('num_img', 0)}</div>"
            )
            builder.append_line("                <div class='stat-label'>Images</div>")
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{stats.get('num_vcf', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>vCard Contacts</div>"
            )
            builder.append_line("            </div>")
            total_messages = (
                stats.get("num_sms", 0)
                + stats.get("num_calls", 0)
                + stats.get("num_voicemails", 0)
            )
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{total_messages}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>Total Items</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("        </div>")

            # Build conversations table
            builder.append_line("        <h2>📁 Conversation Files</h2>")
            builder.append_line("        <table class='conversations-table'>")
            builder.append_line("            <thead>")
            builder.append_line("                <tr>")
            builder.append_line("                    <th>Conversation</th>")
            builder.append_line("                    <th>File Type</th>")
            builder.append_line("                    <th>File Size</th>")
            builder.append_line("                    <th>SMS</th>")
            builder.append_line("                    <th>Calls</th>")
            builder.append_line("                    <th>Voicemails</th>")
            builder.append_line("                    <th>Attachments</th>")
            builder.append_line("                    <th>Latest Message</th>")
            builder.append_line("                </tr>")
            builder.append_line("            </thead>")
            builder.append_line("            <tbody>")

            # Build table rows for each conversation file
            for file_path in conversation_files:
                try:
                    # Get file stats
                    stat = file_path.stat()
                    file_size = stat.st_size

                    # Format file size
                    if file_size is None or file_size < 0:
                        size_str = "Unknown"
                    elif file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        try:
                            size_str = f"{file_size / 1024:.1f} KB"
                        except (TypeError, ZeroDivisionError) as e:
                            size_str = "Unknown"
                            logger.warning(f"Division error in file size calculation: {e}")
                    else:
                        try:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                        except (TypeError, ZeroDivisionError) as e:
                            size_str = "Unknown"
                            logger.warning(f"Division error in file size calculation: {e}")

                    # Get conversation name (without extension)
                    conversation_name = file_path.stem

                    # Get accurate stats from conversation manager
                    conversation_id = file_path.stem
                    conv_stats = self._get_conversation_stats_accurate(conversation_id)

                    # Build table row
                    builder.append_line("                <tr>")
                    builder.append_line(
                        f"                    <td><a href='{file_path.name}' class='file-link'>{conversation_name}</a></td>"
                    )
                    builder.append_line(
                        f"                    <td>{self.output_format.upper()}</td>"
                    )
                    builder.append_line(f"                    <td>{size_str}</td>")
                    builder.append_line(
                        f"                    <td>{conv_stats['sms_count']}</td>"
                    )
                    builder.append_line(
                        f"                    <td>{conv_stats['calls_count']}</td>"
                    )
                    builder.append_line(
                        f"                    <td>{conv_stats['voicemails_count']}</td>"
                    )
                    builder.append_line(
                        f"                    <td>{conv_stats['attachments_count']}</td>"
                    )
                    builder.append_line(
                        f"                    <td>{conv_stats['latest_message_time']}</td>"
                    )
                    builder.append_line("                </tr>")

                except Exception as e:
                    logger.error(f"Failed to get stats for {file_path}: {e}")
                    # Still add the row with basic info
                    conversation_name = file_path.stem
                    builder.append_line("                <tr>")
                    builder.append_line(
                        f"                    <td><a href='{file_path.name}' class='file-link'>{conversation_name}</a></td>"
                    )
                    builder.append_line(
                        f"                    <td>{self.output_format.upper()}</td>"
                    )
                    builder.append_line("                    <td>Unknown</td>")
                    builder.append_line("                    <td>0</td>")
                    builder.append_line("                    <td>0</td>")
                    builder.append_line("                    <td>0</td>")
                    builder.append_line("                    <td>0</td>")
                    builder.append_line("                    <td>Unknown</td>")
                    builder.append_line("                </tr>")

            # Build table footer and HTML footer
            builder.append_line("            </tbody>")
            builder.append_line("        </table>")

            # Build footer
            builder.append_line("        <div class='footer'>")
            builder.append_line(
                "            <p><em>Generated automatically by Google Voice SMS Takeout Converter</em></p>"
            )
            builder.append_line(
                f"            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
            )
            builder.append_line("        </div>")

            builder.append_line("    </div>")
            builder.append_line("</body>")
            builder.append_line("</html>")

            # Write the index.html file
            index_path = self.output_dir / "index.html"
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(builder.build())

            logger.info(
                f"Generated index.html with {len(conversation_files)} conversation files"
            )

        except Exception as e:
            logger.error(f"Failed to generate index.html: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

    def _extract_conversation_stats(
        self, file_path: Path
    ) -> Dict[str, Union[int, str]]:
        """Extract statistics from a conversation file (HTML or XML)."""
        try:
            # Try to get stats from conversation manager first (more accurate)
            conversation_id = file_path.stem
            if conversation_id in self.conversation_stats:
                stats = self.conversation_stats[conversation_id]
                return {
                    "sms_count": stats.get("num_sms", 0),
                    "calls_count": stats.get("num_calls", 0),
                    "voicemails_count": stats.get("num_voicemails", 0),
                    "attachments_count": self._count_real_attachments(stats),
                    "latest_message_time": "From cache"  # Could enhance this
                }

            # Fallback to file parsing if needed
            return self._parse_file_for_stats(file_path)
        except Exception as e:
            logger.error(f"Failed to extract stats from {file_path}: {e}")
            return self._get_default_stats()

    def _parse_file_for_stats(self, file_path: Path) -> Dict[str, Union[int, str]]:
        """Parse file content to extract statistics (fallback method)."""
        try:
            # Read the file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Determine parser based on file extension
            if file_path.suffix.lower() == ".xml":
                # Try to use XML parser for XML files to avoid warnings
                try:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(content, "xml")
                except Exception:
                    # Fall back to HTML parser if XML parser is not available
                    soup = BeautifulSoup(content, "html.parser")
            else:
                # Use HTML parser for HTML files
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(content, "html.parser")

            # Initialize counters
            sms_count = 0
            calls_count = 0
            voicemails_count = 0
            attachments_count = 0
            latest_timestamp = None

            # Find all message rows
            message_rows = soup.find_all("tr")

            for row in message_rows:
                # Check if this row has a message
                message_cell = row.find("td", class_="message")
                if message_cell:
                    message_text = message_cell.get_text().strip()

                    # Count different message types
                    if message_text.startswith("📞"):
                        calls_count += 1
                    elif message_text.startswith("🎙️"):
                        voicemails_count += 1
                    elif (
                        message_text
                        and not message_text.startswith("📞")
                        and not message_text.startswith("🎙️")
                    ):
                        sms_count += 1

                    # Improved attachment detection - only count real attachments
                    attachments_cell = (
                        row.find_all("td")[3] if len(row.find_all("td")) > 3 else None
                    )
                    if attachments_cell:
                        attachments_text = attachments_cell.get_text().strip()
                        # Only count if it's not a placeholder and contains actual attachment indicators
                        if (attachments_text != "-" and 
                            attachments_text and 
                            any(indicator in attachments_text for indicator in ["📷", "📇", "🎵", "🎬", "Image", "vCard", "Audio", "Video"])):
                            attachments_count += 1

                    # Get timestamp for latest message
                    timestamp_cell = row.find("td", class_="timestamp")
                    if timestamp_cell:
                        timestamp_text = timestamp_cell.get_text().strip()
                        if timestamp_text:
                            # Parse timestamp (format: YYYY-MM-DD HH:MM:SS)
                            try:
                                timestamp = datetime.strptime(
                                    timestamp_text, "%Y-%m-%d %H:%M:%S"
                                )
                                if (
                                    latest_timestamp is None
                                    or timestamp > latest_timestamp
                                ):
                                    latest_timestamp = timestamp
                            except ValueError:
                                pass

            # Format latest message time
            if latest_timestamp:
                latest_message_time = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                latest_message_time = "No messages"

            return {
                "sms_count": sms_count,
                "calls_count": calls_count,
                "voicemails_count": voicemails_count,
                "attachments_count": attachments_count,
                "latest_message_time": latest_message_time,
            }

        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return self._get_default_stats()

    def _get_default_stats(self) -> Dict[str, Union[int, str]]:
        """Get default statistics when extraction fails."""
        return {
            "sms_count": 0,
            "calls_count": 0,
            "voicemails_count": 0,
            "attachments_count": 0,
            "latest_message_time": "Error",
        }

    def _finalize_xml_file(
        self, file_info: dict, sorted_messages: list, conversation_id: str
    ):
        """Finalize an XML conversation file."""
        # Pre-allocate header lines to avoid repeated string operations
        header_lines = [
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
            "<!--Converted from GV Takeout data -->",
            f'<smses count="{len(sorted_messages)}">',
        ]

        # Write header efficiently
        file_info["file"].write("\n".join(header_lines) + "\n")

        # Write sorted messages in optimized batches
        batch_size = self._batch_size
        for i in range(0, len(sorted_messages), batch_size):
            batch = sorted_messages[i : i + batch_size]
            # Use generator expression for memory efficiency
            batch_content = "".join(xml_content for _, xml_content in batch)
            file_info["file"].write(batch_content)

        # Write closing tag
        file_info["file"].write("</smses>")
        file_info["file"].close()

        logger.info(
            f"Finalized XML conversation file: {self.get_conversation_filename(conversation_id)} "
            f"with {len(sorted_messages)} messages"
        )

    def _finalize_html_file(
        self, file_info: dict, sorted_messages: list, conversation_id: str
    ):
        """Finalize an HTML conversation file."""
        # Use StringBuilder for efficient HTML generation
        builder = StringBuilder()

        # Build HTML header efficiently
        builder.append_line("<!DOCTYPE html>")
        builder.append_line("<html lang='en'>")
        builder.append_line("<head>")
        builder.append_line("    <meta charset='UTF-8'>")
        builder.append_line(
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        )
        builder.append_line(f"    <title>SMS Conversation - {conversation_id}</title>")
        builder.append_line("    <style>")
        builder.append_line(
            "        body { font-family: Arial, sans-serif; margin: 20px; }"
        )
        builder.append_line(
            "        table { border-collapse: collapse; width: 100%; margin-top: 20px; }"
        )
        builder.append_line(
            "        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
        )
        builder.append_line(
            "        th { background-color: #f2f2f2; font-weight: bold; }"
        )
        builder.append_line("        tr:nth-child(even) { background-color: #f9f9f9; }")
        builder.append_line("        .timestamp { font-size: 0.9em; color: #666; }")
        builder.append_line(
            "        .message { max-width: 400px; word-wrap: break-word; }"
        )
        builder.append_line(
            "        .attachment { color: #0066cc; text-decoration: none; }"
        )
        builder.append_line("        .attachment:hover { text-decoration: underline; }")
        builder.append_line(
            "        .header { background-color: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }"
        )
        builder.append_line("    </style>")
        builder.append_line("</head>")
        builder.append_line("<body>")

        # Build header section
        builder.append_line("    <div class='header'>")
        builder.append_line(f"        <h1>SMS Conversation: {conversation_id}</h1>")
        builder.append_line(f"        <p>Total Messages: {len(sorted_messages)}</p>")
        builder.append_line(
            "        <p><em>Converted from Google Voice Takeout data</em></p>"
        )
        builder.append_line("    </div>")

        # Build table header
        builder.append_line("    <table>")
        builder.append_line("        <thead>")
        builder.append_line("            <tr>")
        builder.append_line("                <th>Timestamp</th>")
        builder.append_line("                <th>Sender</th>")
        builder.append_line("                <th>Message</th>")
        builder.append_line("                <th>Attachments</th>")
        builder.append_line("            </tr>")
        builder.append_line("        </thead>")
        builder.append_line("        <tbody>")

        # Build table rows efficiently
        for timestamp, message_content in sorted_messages:
            # Handle both old format (raw XML content) and new format (pre-extracted content)
            if isinstance(message_content, dict) and "text" in message_content:
                # New format: pre-extracted content
                message_text = message_content["text"]
                # Join attachments and preserve HTML formatting
                if message_content["attachments"]:
                    attachments = " ".join(message_content["attachments"])
                else:
                    attachments = "-"
                sender_display = message_content.get("sender", "-")
            else:
                # Old format: raw XML content - extract message text and attachments
                message_text, attachments = self._extract_message_content(
                    message_content
                )
                # Best-effort sender extraction from raw content
                sender_display = self._extract_sender_from_raw(message_content)

            # Format timestamp
            formatted_time = self._format_timestamp(timestamp)

            # Build table row efficiently
            builder.append_line("            <tr>")
            builder.append_line(
                f"                <td class='timestamp'>{formatted_time}</td>"
            )
            builder.append_line(
                f"                <td class='sender'>{sender_display}</td>"
            )
            builder.append_line(
                f"                <td class='message'>{message_text}</td>"
            )
            builder.append_line(f"                <td>{attachments}</td>")
            builder.append_line("            </tr>")

        # Build HTML footer
        builder.append_line("        </tbody>")
        builder.append_line("    </table>")
        builder.append_line("</body>")
        builder.append_line("</html>")

        # Write the complete HTML content efficiently
        file_info["file"].write(builder.build())
        file_info["file"].close()

        # Clear builder to free memory
        builder.clear()

        logger.info(
            f"Finalized HTML conversation file: {self.get_conversation_filename(conversation_id)} "
            f"with {len(sorted_messages)} messages"
        )

    def _extract_message_content(self, message_content: str) -> tuple[str, str]:
        """Extract message text and attachments from XML content."""
        # Parse the XML content to extract message text and attachments
        try:
            # Simple parsing - look for text content and attachments
            message_text = ""
            attachments = []

            # First try to extract SMS message content from body attribute
            import re

            body_match = re.search(r'body="([^"]*)"', message_content)
            if body_match:
                message_text = body_match.group(1)
                # Unescape XML entities
                message_text = (
                    message_text.replace("&apos;", "'")
                    .replace("&quot;", '"')
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&amp;", "&")
                )
            else:
                # Try to extract MMS message content from part text
                part_text_match = re.search(r'text="([^"]*)"', message_content)
                if part_text_match:
                    message_text = part_text_match.group(1)
                    # Unescape XML entities
                    message_text = (
                        message_text.replace("&apos;", "'")
                        .replace("&quot;", '"')
                        .replace("&lt;", "<")
                        .replace("&gt;", ">")
                        .replace("&amp;", "&")
                    )
                else:
                    # Fallback: look for content between tags
                    text_match = re.search(r"<text>([^<]*)</text>", message_content)
                    if text_match:
                        message_text = text_match.group(1)
                    else:
                        # Last resort: look for content between tags
                        content_match = re.search(r">([^<]+)<", message_content)
                        if content_match:
                            message_text = content_match.group(1)

            # Extract attachments
            # Check for MMS image parts first (more specific)
            if re.search(r'ct="image/[^"]*"', message_content):
                attachments.append("📷 Image")
            # Check for traditional HTML img tags
            elif re.search(r"<img", message_content):
                attachments.append("📷 Image")
            # Check for vCard attachments
            if re.search(r'<a[^>]*class=[\'"]vcard[\'"][^>]*>', message_content):
                attachments.append("📇 vCard")
            # Check for audio attachments
            if re.search(r'ct="audio/[^"]*"', message_content):
                attachments.append("🎵 Audio")
            elif re.search(r"<audio", message_content):
                attachments.append("🎵 Audio")
            # Check for video attachments
            if re.search(r'ct="video/[^"]*"', message_content):
                attachments.append("🎬 Video")
            elif re.search(r"<video", message_content):
                attachments.append("🎬 Video")

            # Clean up message text
            message_text = message_text.strip()
            if not message_text:
                message_text = "[No text content]"

            # Join attachments efficiently
            attachments_str = " ".join(attachments) if attachments else "-"

            return message_text, attachments_str

        except Exception as e:
            # Log the specific error and the content that caused it for debugging
            logger.error(f"Failed to extract message content: {e}")
            logger.debug(f"Problematic content: {message_content[:200]}...")

            # Try to extract any readable text as a last resort
            try:
                # Strip HTML tags and extract any remaining text
                import re

                text_only = re.sub(r"<[^>]+>", "", message_content)
                text_only = re.sub(r"&[^;]+;", " ", text_only)  # Replace HTML entities
                text_only = re.sub(
                    r"\s+", " ", text_only
                ).strip()  # Normalize whitespace

                if text_only and len(text_only) > 5:
                    return (
                        f"[Partial content: {text_only[:100]}{'...' if len(text_only) > 100 else ''}]",
                        "-",
                    )
            except Exception:
                pass

            return "[Error parsing message]", "-"

    def _extract_sender_from_raw(self, message_content: str) -> str:
        """Best-effort sender extraction from raw XML/HTML content for legacy writes."""
        try:
            import re

            # Look for addr entries in MMS XML
            m = re.search(
                r'<addr[^>]*address="([^"]+)"[^>]*type="137"', message_content
            )
            if m:
                return m.group(1)
            # Look for tel: links
            tel_pattern = re.compile(r"tel:([+\d\s\-\(\)]+)")
            m = tel_pattern.search(message_content)
            if m:
                return m.group(1)
            # Fallback
            return "-"
        except Exception:
            return "-"

    def _format_timestamp(self, timestamp: int) -> str:
        """Format timestamp for display."""
        try:
            dt = datetime.fromtimestamp(timestamp / 1000)  # Convert from milliseconds
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(timestamp)

    def get_total_stats(self) -> Dict[str, int]:
        """Get total statistics across all conversations."""
        total_stats = {
            "num_sms": 0,
            "num_img": 0,
            "num_vcf": 0,
            "num_calls": 0,
            "num_voicemails": 0,
            "num_audio": 0,
            "num_video": 0,
            "real_attachments": 0,
        }

        # Count from conversation stats
        for stats in self.conversation_stats.values():
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)

        # Also count from actual message counts if available
        total_messages = 0
        for conversation_id, file_info in self.conversation_files.items():
            if "messages" in file_info:
                total_messages += len(file_info["messages"])

        # If we have message counts but no SMS stats, estimate from messages
        if total_messages > 0 and total_stats["num_sms"] == 0:
            total_stats["num_sms"] = total_messages

        return total_stats

    def update_stats(self, conversation_id: str, stats: Dict[str, int]):
        """Update statistics for a conversation with enhanced attachment tracking."""
        if conversation_id not in self.conversation_stats:
            # Initialize conversation stats with proper structure
            self.conversation_stats[conversation_id] = {
                "num_sms": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "num_img": 0,
                "num_vcf": 0,
                "num_audio": 0,
                "num_video": 0,
                "real_attachments": 0
            }
        
        # Update individual counts
        for key, value in stats.items():
            if key in self.conversation_stats[conversation_id]:
                self.conversation_stats[conversation_id][key] += value
        
        # Calculate real attachment count (only actual attachments, not placeholders)
        self.conversation_stats[conversation_id]["real_attachments"] = (
            self.conversation_stats[conversation_id]["num_img"] +
            self.conversation_stats[conversation_id]["num_vcf"] +
            self.conversation_stats[conversation_id]["num_video"] +
            self.conversation_stats[conversation_id]["num_audio"]
        )

    def _count_real_attachments(self, stats: Dict[str, int]) -> int:
        """Count only real attachments, not placeholders."""
        real_attachments = 0
        real_attachments += stats.get("num_img", 0)  # Images
        real_attachments += stats.get("num_vcf", 0)  # vCards
        real_attachments += stats.get("num_audio", 0)  # Audio files
        real_attachments += stats.get("num_video", 0)  # Video files
        return real_attachments

    def _get_conversation_stats_accurate(self, conversation_id: str) -> Dict[str, Union[int, str]]:
        """Get accurate stats for a conversation from cached data."""
        if conversation_id in self.conversation_stats:
            stats = self.conversation_stats[conversation_id]
            return {
                "sms_count": stats.get("num_sms", 0),
                "calls_count": stats.get("num_calls", 0),
                "voicemails_count": stats.get("num_voicemails", 0),
                "attachments_count": stats.get("real_attachments", 0),
                "latest_message_time": "From cache"  # Could enhance this
            }
        else:
            # Return defaults if no cached stats
            return {
                "sms_count": 0,
                "calls_count": 0,
                "voicemails_count": 0,
                "attachments_count": 0,
                "latest_message_time": "Unknown"
            }
