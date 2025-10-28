"""
AI Summary Generation using Gemini CLI.

This module provides functionality to generate AI-powered summaries
for conversation HTML files using Google's Gemini CLI tool.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    Generates AI summaries for conversation HTML files using Gemini CLI.

    This class:
    1. Parses conversation HTML tables to extract messages
    2. Builds prompts for Gemini CLI
    3. Calls Gemini to generate summaries
    4. Saves/loads summaries to/from JSON files

    Attributes:
        timeout: Timeout in seconds for each Gemini CLI call (default: 60)
        model: Gemini model to use (default: "gemini-pro")
    """

    def __init__(self, timeout: int = 60):
        """
        Initialize the summary generator.

        Args:
            timeout: Timeout per conversation in seconds (default: 60)

        Raises:
            RuntimeError: If Gemini CLI is not installed or not working
        """
        self.timeout = timeout
        self.verify_gemini_available()

    def verify_gemini_available(self) -> None:
        """
        Verify that Gemini CLI is installed and available.

        Raises:
            RuntimeError: If gemini command is not found or not working
        """
        try:
            result = subprocess.run(
                ['which', 'gemini'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "gemini command not found. "
                    "Install from: https://ai.google.dev/gemini-api/docs/cli"
                )

            gemini_path = result.stdout.strip()
            logger.info(f"✅ Gemini CLI found at: {gemini_path}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Failed to verify gemini installation (timeout)")
        except Exception as e:
            raise RuntimeError(f"Failed to verify gemini installation: {e}")

    def get_timeout_for_conversation(self, message_count: int) -> int:
        """
        Calculate adaptive timeout based on conversation size.

        Scales timeout to handle large conversations without hitting
        timeout errors on mega conversations.

        Args:
            message_count: Number of messages in the conversation

        Returns:
            Timeout in seconds:
            - Small (1-100 messages): 120s (2 min)
            - Medium (101-500 messages): 300s (5 min)
            - Large (501-1000 messages): 600s (10 min)
            - Mega (1000+ messages): 900s (15 min)
        """
        if message_count <= 100:
            return 120  # 2 minutes
        elif message_count <= 500:
            return 300  # 5 minutes
        elif message_count <= 1000:
            return 600  # 10 minutes
        else:
            return 900  # 15 minutes

    def extract_messages_from_html(self, html_path: Path) -> List[Dict]:
        """
        Parse conversation HTML and extract messages from TABLE structure.

        The conversation HTML uses a table with columns:
        - Timestamp (datetime string like "2024-11-25 16:09:04")
        - Sender (conversation participant name)
        - Message (text content, may include call/voicemail indicators)
        - Attachments (optional attachment links)

        Args:
            html_path: Path to conversation HTML file

        Returns:
            List of message dicts with keys: timestamp, sender, text, type
            Returns empty list if parsing fails or no messages found
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            messages = []

            # Find the conversation table
            table = soup.find('table')
            if not table:
                logger.warning(f"No table found in {html_path.name}")
                return []

            # Find tbody (or fallback to all rows if no tbody)
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                # Fallback: get all rows and skip header row
                all_rows = table.find_all('tr')
                rows = all_rows[1:] if len(all_rows) > 1 else all_rows

            # Parse each row
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:  # Need at least timestamp, sender, message
                    timestamp_str = cells[0].text.strip()
                    sender = cells[1].text.strip()
                    text = cells[2].text.strip()

                    # Skip empty messages
                    if not text:
                        continue

                    # Detect message type by emoji indicators
                    msg_type = 'sms'
                    if '📞' in text:
                        msg_type = 'call'
                    elif '🎙️' in text:
                        msg_type = 'voicemail'

                    messages.append({
                        'timestamp': timestamp_str,
                        'sender': sender,
                        'text': text,
                        'type': msg_type
                    })

            logger.debug(f"Extracted {len(messages)} messages from {html_path.name}")
            return messages

        except Exception as e:
            logger.error(f"Failed to parse {html_path.name}: {e}")
            return []

    def _calculate_date_range(self, messages: List[Dict]) -> str:
        """
        Calculate date range from message timestamps.

        Args:
            messages: List of message dicts with 'timestamp' key

        Returns:
            Date range string like "2024-01-15 to 2024-01-20"
            Returns "Unknown" if no valid dates found
        """
        if not messages:
            return "Unknown"

        dates = []
        for msg in messages:
            timestamp_str = msg.get('timestamp', '')
            if timestamp_str:
                try:
                    # Parse format: "2024-11-25 16:09:04"
                    # Extract just the date part
                    date_part = timestamp_str.split()[0]  # Get "2024-11-25"
                    dates.append(date_part)
                except:
                    continue

        if dates:
            return f"{min(dates)} to {max(dates)}"
        return "Unknown"

    def build_gemini_prompt(self, messages: List[Dict], conversation_id: str) -> str:
        """
        Build prompt string for Gemini CLI.

        Includes ALL messages in the conversation (no sampling).
        Uses adaptive timeout to handle large conversations.

        Args:
            messages: List of message dicts
            conversation_id: Conversation identifier (filename stem)

        Returns:
            Formatted prompt string for Gemini
        """
        # Build message list - include ALL messages (no sampling)
        message_lines = []
        for msg in messages:
            sender = msg.get('sender', 'Unknown')
            text = msg.get('text', '')  # Full message text, no truncation
            message_lines.append(f"{sender}: {text}")

        date_range = self._calculate_date_range(messages)
        message_text = f"(showing all {len(messages)} messages)"

        prompt = f"""Generate a detailed summary for this conversation with "{conversation_id}".

Messages {message_text} from {date_range}:
{chr(10).join(message_lines)}

Provide a comprehensive paragraph (3-5 sentences) covering:
- Purpose of the conversation
- Key topics discussed
- Important decisions or outcomes
- Overall context (business/personal/legal/service-related/etc.)

Focus on facts and substance. Be specific and informative."""

        return prompt

    def generate_summary(self, html_path: Path) -> Optional[Dict]:
        """
        Generate AI summary for a conversation using Gemini CLI.

        This method:
        1. Extracts messages from HTML
        2. Builds a prompt
        3. Calls Gemini CLI via subprocess with adaptive timeout
        4. Validates the output
        5. Returns summary dict or None on failure

        Args:
            html_path: Path to conversation HTML file

        Returns:
            Dict with keys: summary, generated_at, message_count, date_range, model
            Returns None if generation fails (errors are logged)
        """
        try:
            # Extract messages
            messages = self.extract_messages_from_html(html_path)
            if not messages:
                logger.warning(f"No messages found in {html_path.name}")
                return None

            # Calculate adaptive timeout based on conversation size
            adaptive_timeout = self.get_timeout_for_conversation(len(messages))

            # Build prompt
            prompt = self.build_gemini_prompt(messages, html_path.stem)

            # Call Gemini CLI
            # Format: gemini -o text "prompt"
            # Note: Not specifying model - let Gemini use default (gemini-2.5-pro)
            cmd = ['gemini', '-o', 'text', prompt]

            logger.debug(f"Calling Gemini for {html_path.name}...")
            logger.debug(f"Command: {' '.join(cmd[:4])} [prompt_length={len(prompt)}]")
            logger.debug(f"Message count: {len(messages)}, adaptive timeout: {adaptive_timeout}s")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=adaptive_timeout
            )

            # Check return code
            if result.returncode != 0:
                logger.error(
                    f"Gemini failed for {html_path.name} "
                    f"(exit code {result.returncode})"
                )
                if result.stderr:
                    logger.error(f"  stderr: {result.stderr[:200]}")
                return None

            # Get summary from stdout
            summary = result.stdout.strip()
            logger.debug(f"Gemini stdout length: {len(result.stdout)}, stderr length: {len(result.stderr)}")
            if not summary:
                logger.warning(f"Empty stdout from Gemini for {html_path.name}")
                logger.warning(f"  stderr: {result.stderr[:200]}")
                logger.warning(f"  stdout: '{result.stdout[:200]}'")
                logger.warning(f"  Command was: {cmd[:4]} [prompt={prompt[:100]}...]")

            # Validate output
            if not summary or len(summary) < 20:
                logger.warning(
                    f"Suspiciously short summary for {html_path.name}: '{summary}'"
                )
                return None

            # Check for refusals
            if "I cannot" in summary or "I can't" in summary or "As an AI" in summary:
                logger.warning(f"Gemini refused to summarize {html_path.name}")
                return None

            # Success!
            logger.info(f"✅ Generated summary for {html_path.name}")
            return {
                'summary': summary,
                'generated_at': datetime.now().isoformat(),
                'message_count': len(messages),
                'date_range': self._calculate_date_range(messages),
                'model': 'gemini-2.5-pro'  # Track which model generated this summary
            }

        except subprocess.TimeoutExpired as e:
            # Use adaptive timeout in error message
            timeout_used = self.get_timeout_for_conversation(len(messages)) if messages else self.timeout
            logger.error(f"Gemini timeout ({timeout_used}s) for {html_path.name}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {html_path.name}: {e}")
            return None

    def save_summaries(self, summaries_dict: Dict, output_path: Path) -> None:
        """
        Save summaries to JSON file with metadata.

        JSON structure includes:
        - version: Format version (1.1 with model tracking)
        - generated_at: Timestamp
        - generated_by: Tool info
        - stats: Statistics about summaries
        - model_usage: Count of summaries per model
        - summaries: The actual summary data

        Args:
            summaries_dict: Dict mapping conversation_id to summary dict
            output_path: Path to output JSON file
        """
        # Calculate model usage statistics
        model_usage = {}
        for summary_data in summaries_dict.values():
            model = summary_data.get('model', 'unknown')
            model_usage[model] = model_usage.get(model, 0) + 1

        output_dict = {
            'version': '1.1',  # Bumped for model tracking support
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'Gemini CLI',
            'stats': {
                'total_conversations': len(summaries_dict),
                'total_characters': sum(
                    len(s['summary']) for s in summaries_dict.values()
                )
            },
            'model_usage': model_usage,  # Track which models generated summaries
            'summaries': summaries_dict
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Saved {len(summaries_dict)} summaries to {output_path}")

    def load_summaries(self, json_path: Path) -> Dict:
        """
        Load existing summaries from JSON file.

        Used for merging new summaries with existing ones.

        Args:
            json_path: Path to summaries JSON file

        Returns:
            Dict mapping conversation_id to summary dict
            Returns empty dict if file doesn't exist or can't be loaded
        """
        if not json_path.exists():
            return {}

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('summaries', {})
        except Exception as e:
            logger.warning(f"Could not load {json_path}: {e}")
            return {}
