"""
Conversation Manager for SMS/MMS processing.

This module handles the creation and management of conversation files
for different senders/groups during SMS/MMS conversion.
"""

import logging
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from core.processing_config import ProcessingConfig

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
        output_format: str = "html",
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
        if not isinstance(output_format, str) or output_format != "html":
            raise ValueError(f"output_format must be 'html', got {output_format}")

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

                # Note: Individual contact filtering is now handled at the conversation level
                # in sms.py, so this check is no longer needed here
                if phone_lookup_manager:
                    alias = phone_lookup_manager.get_alias(phone_number, None)
                else:
                    alias = phone_number
                return alias
            else:
                return "unknown"

    def get_conversation_filename(self, conversation_id: str) -> Path:
        """Get the filename for a conversation."""
        return self.output_dir / f"{conversation_id}.html"

    def _open_conversation_file(self, conversation_id: str):
        """Open a conversation file for writing."""
        if conversation_id not in self.conversation_files:
            # Create new conversation file with optimized buffer size
            filename = self.get_conversation_filename(conversation_id)
            # Ensure the output directory exists
            filename.parent.mkdir(parents=True, exist_ok=True)
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

            # Initialize conversation stats with consistent keys
            self.conversation_stats[conversation_id] = {
                "sms_count": 0,
                "calls_count": 0,
                "voicemails_count": 0,
                "attachments_count": 0,
                "latest_timestamp": 0,
                "latest_message_time": "No messages"
            }

    def write_message(self, conversation_id: str, message_content: str, timestamp: int):
        """Write a message to the conversation file with optimized buffering."""
        with self._lock:
            # Ensure the conversation file is open
            if conversation_id not in self.conversation_files:
                self._open_conversation_file(conversation_id)

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
        timestamp: int,  # Unix timestamp in milliseconds
        sender: str,
        message: str,
        attachments: list = None,
        message_type: str = "sms",  # Type: "sms", "call", "voicemail"
        config: Optional["ProcessingConfig"] = None,  # Add config for date filtering
    ):
        """Write a message to a conversation file with content."""
        with self._lock:
            # ENHANCEMENT: Apply date filtering at message write time
            if self._should_skip_by_date_filter(timestamp, config):
                logger.debug(f"Skipping message due to date filter: timestamp={timestamp}")
                return  # Don't write the message
            
            # Ensure the conversation file is open
            if conversation_id not in self.conversation_files:
                # This case should ideally not be hit if get_conversation_id is always called first
                self._open_conversation_file(conversation_id)

            file_info = self.conversation_files.get(conversation_id)
            if not file_info:
                logger.error(f"Failed to get file_info for {conversation_id} after opening.")
                return

            # Convert timestamp to formatted string for display
            formatted_time = self._format_timestamp(timestamp)
            
            # Append the message to the internal buffer with actual timestamp
            message_data = {
                "text": message,
                "attachments": attachments or [],
                "sender": sender,
                "formatted_time": formatted_time,
                "raw_content": None,  # Not needed for HTML output
            }
            file_info["messages"].append((timestamp, message_data))  # Use actual timestamp
            file_info["buffer_size"] += len(message)

            # Update conversation statistics based on message type
            # Ensure stats are initialized (defensive programming)
            if conversation_id not in self.conversation_stats:
                self.conversation_stats[conversation_id] = {
                    "sms_count": 0,
                    "calls_count": 0,
                    "voicemails_count": 0,
                    "attachments_count": 0,
                    "latest_timestamp": 0,
                    "latest_message_time": "No messages"
                }
            
            # Track different message types separately
            if message_type == "sms":
                self.conversation_stats[conversation_id]['sms_count'] += 1
                pass  # SMS count incremented
            elif message_type == "call":
                self.conversation_stats[conversation_id]['calls_count'] += 1
            elif message_type == "voicemail":
                self.conversation_stats[conversation_id]['voicemails_count'] += 1
            else:
                # Default to SMS for unknown types
                self.conversation_stats[conversation_id]['sms_count'] += 1
            
            # Count attachments if present
            if attachments:
                self.conversation_stats[conversation_id]['attachments_count'] += len(attachments)
            
            # Update latest message info
            self.conversation_stats[conversation_id]['latest_timestamp'] = timestamp
            self.conversation_stats[conversation_id]['latest_message_time'] = formatted_time

            # Memory-only buffering: No premature flushing to files
            # All messages are kept in memory until finalization

    # _flush_buffer_to_file method removed - using memory-only buffering
    # Messages are kept in memory until finalization to ensure clean HTML output

    def finalize_conversation_files(self):
        """Finalize all conversation files by writing headers and closing tags."""
        with self._lock:
            for conversation_id, file_info in self.conversation_files.items():
                try:
                    # Sort messages by timestamp (using tuple unpacking for better performance)
                    sorted_messages = sorted(file_info["messages"], key=lambda x: x[0])

                    self._finalize_html_file(
                        file_info, sorted_messages, conversation_id
                    )

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
            # Use template-based generation for consistency and maintainability
            return self._generate_index_html_with_template(stats, elapsed_time)
        except Exception as e:
            logger.error(f"Template-based index generation failed: {e}")
            logger.info("Falling back to manual HTML generation")
            return self._generate_index_html_manual(stats, elapsed_time)
    
    def _generate_index_html_with_template(self, stats: Dict[str, int], elapsed_time: float):
        """Generate index.html using the template (preferred method)."""
        try:
            # Load the index template
            template_path = Path(__file__).parent.parent / "templates" / "index.html"
            if not template_path.exists():
                raise FileNotFoundError(f"Index template not found: {template_path}")
            
            template_content = template_path.read_text()
            
            # Get conversation files
            conversation_files = []
            for file_path in self.output_dir.glob("*.html"):
                if file_path.name != "index.html":
                    conversation_files.append(file_path)
            conversation_files.sort(key=lambda x: x.name)
            
            # Use internal stats if passed stats are empty
            internal_stats = self.get_total_stats()
            effective_stats = stats
            
            if (stats.get('num_sms', 0) == 0 and stats.get('num_calls', 0) == 0 and 
                stats.get('num_voicemails', 0) == 0 and
                (internal_stats.get('num_sms', 0) > 0 or internal_stats.get('num_calls', 0) > 0 or 
                 internal_stats.get('num_voicemails', 0) > 0)):
                logger.info("Using internal ConversationManager stats for index generation")
                effective_stats = internal_stats
            
            # Build conversation rows
            conversation_rows = self._build_conversation_rows(conversation_files)
            
            # Calculate total messages
            total_messages = (
                effective_stats.get("num_sms", 0) + 
                effective_stats.get("num_calls", 0) + 
                effective_stats.get("num_voicemails", 0)
            )
            
            # Format template variables
            template_vars = {
                'elapsed_time': f"{elapsed_time:.2f}",
                'total_conversations': len(conversation_files),
                'num_sms': effective_stats.get('num_sms', 0),
                'num_calls': effective_stats.get('num_calls', 0),
                'num_voicemails': effective_stats.get('num_voicemails', 0),
                'num_img': effective_stats.get('num_img', 0),
                'num_vcf': effective_stats.get('num_vcf', 0),
                'total_messages': total_messages,
                'conversation_rows': conversation_rows,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Replace template variables
            html_content = template_content.format(**template_vars)
            
            # Write the index file
            index_file = self.output_dir / "index.html"
            index_file.write_text(html_content, encoding='utf-8')
            
            logger.info(f"Generated index.html with {len(conversation_files)} conversations using template")
            return
            
        except Exception as e:
            logger.error(f"Template-based index generation failed: {e}")
            raise
    
    def _build_conversation_rows(self, conversation_files: List[Path]) -> str:
        """Build HTML table rows for conversation files."""
        if not conversation_files:
            return "<tr><td colspan='8'><em>No conversation files found</em></td></tr>"
        
        rows = []
        for file_path in conversation_files:
            try:
                # Get file stats
                file_size = file_path.stat().st_size
                file_size_str = f"{file_size / 1024:.1f} KB" if file_size > 0 else "0 KB"
                
                # Get conversation stats if available
                conversation_id = file_path.stem
                conv_stats = self._get_conversation_stats_accurate(conversation_id)
                # Debug info removed for cleaner output
                
                # Build row
                row = f"""
                <tr>
                    <td><a href='{file_path.name}' class='file-link'>{conversation_id}</a></td>
                    <td>HTML</td>
                    <td>{file_size_str}</td>
                    <td>{conv_stats.get('sms_count', 0)}</td>
                    <td>{conv_stats.get('calls_count', 0)}</td>
                    <td>{conv_stats.get('voicemails_count', 0)}</td>
                    <td>{conv_stats.get('attachments_count', 0)}</td>
                    <td class='metadata'>{conv_stats.get('latest_message_time', 'No messages')}</td>
                </tr>"""
                rows.append(row)
            except Exception as e:
                logger.warning(f"Failed to build row for {file_path.name}: {e}")
                continue
        
        return "\n".join(rows)
    
    def _generate_index_html_manual(self, stats: Dict[str, int], elapsed_time: float):
        """Generate index.html manually (fallback method)."""
        try:
            # Get all conversation files in the output directory
            conversation_files = []
            for file_path in self.output_dir.glob("*.html"):
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

            # Build summary stats section - use internal stats if passed stats are empty
            internal_stats = self.get_total_stats()
            effective_stats = stats
            
            # If passed stats are all zeros but we have internal stats, use internal stats
            if (stats.get('num_sms', 0) == 0 and stats.get('num_calls', 0) == 0 and 
                stats.get('num_voicemails', 0) == 0 and
                (internal_stats.get('num_sms', 0) > 0 or internal_stats.get('num_calls', 0) > 0 or 
                 internal_stats.get('num_voicemails', 0) > 0)):
                logger.info("Using internal ConversationManager stats instead of passed stats (passed stats appear to be empty)")
                effective_stats = internal_stats
            
            builder.append_line("        <div class='stats-grid'>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{effective_stats.get('num_sms', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>SMS Messages</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{effective_stats.get('num_calls', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>Call Logs</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{effective_stats.get('num_voicemails', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>Voicemails</div>"
            )
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{effective_stats.get('num_img', 0)}</div>"
            )
            builder.append_line("                <div class='stat-label'>Images</div>")
            builder.append_line("            </div>")
            builder.append_line("            <div class='stat-card'>")
            builder.append_line(
                f"                <div class='stat-number'>{effective_stats.get('num_vcf', 0)}</div>"
            )
            builder.append_line(
                "                <div class='stat-label'>vCard Contacts</div>"
            )
            builder.append_line("            </div>")
            total_messages = (
                effective_stats.get("num_sms", 0)
                + effective_stats.get("num_calls", 0)
                + effective_stats.get("num_voicemails", 0)
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

                    # Skip conversations with no messages (safety net)
                    total_messages = (conv_stats['sms_count'] + conv_stats['calls_count'] + 
                                     conv_stats['voicemails_count'])
                    
                    # If stats are missing but file exists and has content, estimate from file
                    if total_messages == 0 and file_size > 100:  # File has content
                        logger.debug(f"No cached stats for {file_path.name}, estimating from file content")
                        # Estimate stats from file content for display purposes
                        conv_stats = {
                            'sms_count': 1,  # Assume at least 1 message if file has content
                            'calls_count': 0,
                            'voicemails_count': 0,
                            'attachments_count': 0,
                            'latest_message_time': 'Unknown'
                        }
                        total_messages = 1
                    
                    if total_messages == 0:
                        logger.debug(f"Skipping empty conversation file: {file_path.name}")
                        continue

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
                    "latest_message_time": stats.get("latest_message_time", "No messages")
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


    def _finalize_html_file(
        self, file_info: dict, sorted_messages: list, conversation_id: str
    ):
        """Finalize an HTML conversation file."""
        try:
            # Validate message data
            valid_messages = [msg for msg in sorted_messages if self._validate_message_data(msg[1])]
            
            if not valid_messages:
                logger.warning(f"No valid messages found for conversation {conversation_id}")
                self._write_error_page(file_info, conversation_id, "No valid messages found")
                return
            
            from templates.loader import format_conversation_template
            
            # Build message rows from sorted messages
            message_rows = []
            for timestamp, message_data in valid_messages:
                # Extract message content from dictionary (HTML output only)
                text = message_data.get('text', '')
                attachments = message_data.get('attachments', [])
                sender = message_data.get('sender', 'Unknown')
                
                # Use pre-formatted timestamp from message data
                formatted_time = message_data.get('formatted_time', self._format_timestamp(timestamp))
                
                # Build attachments HTML
                attachments_html = self._build_attachments_html(attachments)
                
                # Create message row
                row = self._build_message_row(formatted_time, sender, text, attachments_html)
                message_rows.append(row)
            
            # Get conversation metadata
            date_range = self._get_conversation_date_range(valid_messages)
            
            # Build HTML using template
            html_content = format_conversation_template(
                conversation_id=conversation_id,
                total_messages=len(valid_messages),
                message_rows="\n".join(message_rows),
                date_range=date_range
            )
            
            # Write and close file
            file_info["file"].write(html_content)
            file_info["file"].close()
            
            logger.info(f"Successfully finalized conversation {conversation_id} with {len(valid_messages)} messages")
            
        except Exception as e:
            logger.error(f"ERROR: Failed to finalize HTML file for {conversation_id}: {e}")
            self._write_error_page(file_info, conversation_id, str(e))

    # _extract_message_content function removed - only HTML output supported

    # _extract_sender_from_raw function removed - only HTML output supported

    def _validate_message_data(self, message_data: dict) -> bool:
        """Validate message data before processing."""
        required_fields = ['text', 'sender', 'formatted_time']
        return all(field in message_data for field in required_fields)

    def _write_error_page(self, file_info: dict, conversation_id: str, error_message: str):
        """Write an error page when HTML generation fails."""
        error_content = f"""<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>Error - {conversation_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .error {{ background-color: #ffe6e6; padding: 20px; border-radius: 5px; border: 1px solid #ff9999; }}
    </style>
</head>
<body>
    <div class='error'>
        <h1>Error Generating Conversation</h1>
        <p><strong>Conversation ID:</strong> {conversation_id}</p>
        <p><strong>Error:</strong> {error_message}</p>
        <p><em>Please check the logs for more details.</em></p>
    </div>
</body>
</html>"""
        file_info["file"].write(error_content)
        file_info["file"].close()

    def _build_attachments_html(self, attachments: list) -> str:
        """Build HTML for attachments."""
        if not attachments:
            return ""
        
        attachment_links = []
        for attachment in attachments:
            if isinstance(attachment, dict) and 'filename' in attachment:
                attachment_links.append(f'<a href="{attachment["filename"]}" class="attachment">📎 {attachment["filename"]}</a>')
            elif isinstance(attachment, str) and attachment:
                attachment_links.append(f'<span class="attachment">📎 {attachment}</span>')
        
        return "<br>".join(attachment_links) if attachment_links else ""

    def _build_message_row(self, formatted_time: str, sender: str, text: str, attachments_html: str) -> str:
        """Build a single message row HTML."""
        # Escape HTML characters in text
        import html
        escaped_text = html.escape(text)
        
        return f"""
                <tr>
                    <td class="timestamp">{formatted_time}</td>
                    <td class="sender">{html.escape(sender)}</td>
                    <td class="message">{escaped_text}</td>
                    <td class="attachments">{attachments_html}</td>
                </tr>"""

    def _get_conversation_date_range(self, messages: list) -> str:
        """Get the date range for a conversation."""
        if not messages:
            return "No messages"
        
        timestamps = [msg[0] for msg in messages]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        
        try:
            from datetime import datetime
            min_date = datetime.fromtimestamp(min_ts / 1000).strftime("%Y-%m-%d")
            max_date = datetime.fromtimestamp(max_ts / 1000).strftime("%Y-%m-%d")
            
            if min_date == max_date:
                return min_date
            else:
                return f"{min_date} to {max_date}"
        except Exception:
            return "Unknown date range"

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

        # Count from conversation stats (with proper key mapping)
        for stats in self.conversation_stats.values():
            total_stats["num_sms"] += stats.get('sms_count', 0)
            total_stats["num_calls"] += stats.get('calls_count', 0)
            total_stats["num_voicemails"] += stats.get('voicemails_count', 0)
            total_stats["num_img"] += stats.get('attachments_count', 0)
            total_stats["real_attachments"] += stats.get('attachments_count', 0)

        # Fallback: Count from actual message counts if statistics are missing
        total_messages = 0
        for conversation_id, file_info in self.conversation_files.items():
            if "messages" in file_info:
                total_messages += len(file_info["messages"])

        # If we have message counts but no SMS stats, use fallback (should rarely happen now)
        if total_messages > 0 and total_stats["num_sms"] == 0:
            logger.warning(f"Statistics tracking failed - using fallback count: {total_messages} messages")
            total_stats["num_sms"] = total_messages

        return total_stats

    def _should_skip_by_date_filter(self, timestamp: int, config: Optional["ProcessingConfig"]) -> bool:
        """
        Determine if a message should be skipped based on date filtering configuration.
        
        Args:
            timestamp: Unix timestamp in milliseconds
            config: ProcessingConfig containing date filter settings
            
        Returns:
            bool: True if message should be skipped due to date filtering, False otherwise
        """
        if not config or (config.older_than is None and config.newer_than is None):
            return False  # No date filtering enabled
        
        try:
            from datetime import datetime
            message_date = datetime.fromtimestamp(timestamp / 1000.0)
            
            # Check older-than filter (skip messages at or after this date)
            if config.older_than and message_date >= config.older_than:
                return True
            
            # Check newer-than filter (skip messages at or before this date)  
            if config.newer_than and message_date <= config.newer_than:
                return True
                
            return False
        except Exception:
            return False  # Don't skip on parsing errors

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
                "real_attachments": 0,
                "latest_timestamp": 0,
                "latest_message_time": "No messages"
            }
        
        # Update individual counts
        for key, value in stats.items():
            if key in self.conversation_stats[conversation_id]:
                self.conversation_stats[conversation_id][key] += value
        
        # Calculate real attachment count (only actual attachments, not placeholders)
        # DEFENSIVE PROGRAMMING: Use .get() to handle missing keys gracefully
        conv_stats = self.conversation_stats[conversation_id]
        self.conversation_stats[conversation_id]["real_attachments"] = (
            conv_stats.get("num_img", 0) +
            conv_stats.get("num_vcf", 0) +
            conv_stats.get("num_video", 0) +
            conv_stats.get("num_audio", 0)
        )

    def update_latest_timestamp(self, conversation_id: str, timestamp: int):
        """Update the latest message timestamp for a conversation."""
        if conversation_id not in self.conversation_stats:
            # Initialize conversation stats if not exists
            self.conversation_stats[conversation_id] = {
                "num_sms": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "num_img": 0,
                "num_vcf": 0,
                "num_audio": 0,
                "num_video": 0,
                "real_attachments": 0,
                "latest_timestamp": 0,
                "latest_message_time": "No messages"
            }
        
        # Update latest timestamp if this message is newer
        current_latest = self.conversation_stats[conversation_id].get("latest_timestamp", 0)
        if timestamp > current_latest:
            self.conversation_stats[conversation_id]["latest_timestamp"] = timestamp
            # Format timestamp for display
            try:
                from datetime import datetime
                formatted_time = datetime.fromtimestamp(timestamp / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
                self.conversation_stats[conversation_id]["latest_message_time"] = formatted_time
            except Exception as e:
                logger.warning(f"Failed to format timestamp {timestamp} for conversation {conversation_id}: {e}")
                self.conversation_stats[conversation_id]["latest_message_time"] = "Invalid timestamp"

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
                "sms_count": stats.get("sms_count", 0),
                "calls_count": stats.get("calls_count", 0),
                "voicemails_count": stats.get("voicemails_count", 0),
                "attachments_count": stats.get("attachments_count", 0),
                "latest_message_time": stats.get("latest_message_time", "No messages")
            }
        else:
            # Return defaults if no cached stats
            return {
                "sms_count": 0,
                "calls_count": 0,
                "voicemails_count": 0,
                "attachments_count": 0,
                "latest_message_time": "No messages"
            }
